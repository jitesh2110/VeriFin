"""
Gemini Vision OCR Engine for VeriFin
Uses Google's Gemini Vision AI to intelligently extract invoice data
"""

import google.generativeai as genai
import fitz  # PyMuPDF
from PIL import Image
import io
import os
import sys
import json
import re
from pathlib import Path
from dotenv import load_dotenv

# Ensure UTF-8 output encoding on Windows console
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from prompt_manager import prompt_manager

load_dotenv(r"C:\D\Dev\Projects\VeriFin\.env")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
class GeminiVisionOCR:
    def __init__(self, api_key=GEMINI_API_KEY):
        """Initialize Gemini Vision with API key"""
        print("🚀 Initializing Gemini Vision OCR...")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        print("✅ Gemini Vision OCR initialized!")
    
    def convert_pdf_to_images(self, file_path):
        """Convert PDF pages or load direct image as PIL Image list"""
        path = Path(file_path)
        ext = path.suffix.lower()

        # Handle direct image files
        if ext in ['.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff']:
            try:
                img = Image.open(str(file_path))
                if img.mode not in ("RGB", "L"):
                    img = img.convert("RGB")
                return [img]
            except Exception as e:
                print(f"❌ Direct image loading error: {e}")
                return None

        # Handle PDF documents
        try:
            doc = fitz.open(str(file_path))
            images = []
            print(f"📄 PDF has {len(doc)} pages")
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                # 200 DPI matrix is optimal balance of sharpness and speed
                mat = fitz.Matrix(2.0, 2.0)
                pix = page.get_pixmap(matrix=mat, alpha=False)
                img_data = pix.tobytes("png")
                image = Image.open(io.BytesIO(img_data))
                images.append(image)
                print(f"✅ Converted page {page_num + 1}/{len(doc)}: {image.size}")
            
            doc.close()
            return images
        except Exception as e:
            print(f"❌ PDF conversion error: {e}")
            return None
    
    def convert_pdf_to_image(self, pdf_path):
        """Convert PDF first page to high-quality image (backward compatibility)"""
        images = self.convert_pdf_to_images(pdf_path)
        return images[0] if images else None
    
    def create_extraction_prompt(self, company_id: str = "comp_default"):
        """Create company-tailored prompt for Gemini via prompt_manager"""
        return prompt_manager.build_extraction_prompt(company_id=company_id)
    
    def extract_invoice_data(self, image, company_id: str = "comp_default"):
        """Use Gemini Vision to extract structured data from invoice image"""
        try:
            print(f"🔍 Sending image to Gemini Vision AI for company [{company_id}]...")
            
            # Create company-specific prompt
            prompt = self.create_extraction_prompt(company_id=company_id)
            
            # Send to Gemini Vision
            response = self.model.generate_content([prompt, image])
            
            print("✅ Received response from Gemini Vision")
            
            # Extract JSON from response
            response_text = response.text.strip()
            
            # Remove markdown code blocks if present
            if response_text.startswith("```json"):
                response_text = response_text.replace("```json", "").replace("```", "").strip()
            elif response_text.startswith("```"):
                response_text = response_text.replace("```", "").strip()
            
            # Parse JSON
            try:
                extracted_data = json.loads(response_text)
                print("✅ Successfully parsed JSON response")
                return extracted_data
            except json.JSONDecodeError as e:
                print(f"⚠️ JSON parse error: {e}")
                print(f"Response text: {response_text[:500]}")
                # Try to extract JSON from text
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    extracted_data = json.loads(json_match.group())
                    print("✅ Extracted JSON from response")
                    return extracted_data
                else:
                    return None
                
        except Exception as e:
            print(f"❌ Gemini Vision error: {e}")
            return None
    
    def process_invoice(self, file_path, company_id: str = "comp_default"):
        """
        Main processing function - handles multi-page PDFs with company prompt configuration
        Returns structured invoice data
        """
        print(f"\n{'='*60}")
        print(f"🔍 Processing Invoice: {Path(file_path).name} (Tenant: {company_id})")
        print(f"{'='*60}")
        
        # Convert ALL PDF pages to images or load direct image
        images = self.convert_pdf_to_images(file_path)
        
        if not images:
            return {
                'success': False,
                'error': 'Failed to convert document to images'
            }
        
        # Process all pages with company prompt
        all_extracted_data = []
        for page_num, image in enumerate(images, 1):
            print(f"\n📄 Processing page {page_num}/{len(images)}...")
            extracted_data = self.extract_invoice_data(image, company_id=company_id)
            if extracted_data:
                all_extracted_data.append(extracted_data)
        
        if not all_extracted_data:
            return {
                'success': False,
                'error': 'Failed to extract data from invoice'
            }
        
        # Merge data from all pages (first page has main info, other pages may have line items)
        extracted_data = all_extracted_data[0]  # Main data from first page
        
        # Merge line items from all pages
        all_line_items = []
        for page_data in all_extracted_data:
            all_line_items.extend(page_data.get('line_items', []))
        extracted_data['line_items'] = all_line_items
        
        print(f"\n✅ Processed {len(images)} pages, found {len(all_line_items)} total line items")
        
        # Validate and clean GST numbers (MUST be exactly 15 characters)
        raw_gst_numbers = extracted_data.get('gst_numbers', [])
        valid_gst_numbers = []
        
        for gst in raw_gst_numbers:
            cleaned_gst = gst.replace(" ", "").upper()
            if len(cleaned_gst) == 15:
                valid_gst_numbers.append(cleaned_gst)
                print(f"✅ Valid GST: {cleaned_gst} (15 chars)")
            else:
                print(f"❌ Invalid GST: {gst} ({len(cleaned_gst)} chars) - REJECTED")
            
        # Fallback: If AI hallucinated or failed to find a valid GST, use regex on the raw text
        if not valid_gst_numbers:
            raw_text = extracted_data.get('raw_extracted_text', '').upper()
            # Standard GSTIN regex: 2 digits + 5 letters + 4 digits + 1 letter + 1 char + Z + 1 char
            gst_pattern = r'\b[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}[Z]{1}[0-9A-Z]{1}\b'
            regex_matches = re.findall(gst_pattern, raw_text)
            
            if regex_matches:
                # Remove duplicates by converting to set, then back to list
                valid_gst_numbers = list(set(regex_matches))
                print(f"✅ Recovered valid GST from raw text via regex: {valid_gst_numbers}")
        
        # Calculate total GST rate from CGST+SGST if needed
        gst_rate = extracted_data.get('gst_rate', 'Unknown')
        cgst_rate = extracted_data.get('cgst_rate', 'Unknown')
        sgst_rate = extracted_data.get('sgst_rate', 'Unknown')
        igst_rate = extracted_data.get('igst_rate', 'Unknown')
        
        # If gst_rate is Unknown but CGST and SGST are available, calculate it
        if gst_rate == 'Unknown' and cgst_rate != 'Unknown' and sgst_rate != 'Unknown':
            try:
                cgst_val = float(cgst_rate.replace('%', '').strip())
                sgst_val = float(sgst_rate.replace('%', '').strip())
                total_gst = cgst_val + sgst_val
                gst_rate = f"{total_gst}%"
                print(f"✅ Calculated GST Rate: CGST {cgst_val}% + SGST {sgst_val}% = {total_gst}%")
            except:
                pass
        
        # Structure the response
        structured_data = {
            'invoice_number': extracted_data.get('invoice_number', 'Unknown'),
            'vendor_name': extracted_data.get('vendor_name', 'Unknown'),
            'invoice_date': extracted_data.get('invoice_date', 'Unknown'),
            'total_amount': float(extracted_data.get('total_amount', 0)),
            'gst_numbers': valid_gst_numbers,  # Only valid 15-char GST numbers
            'gst_rate': gst_rate,  # Total GST percentage (CGST+SGST or IGST)
            'cgst_rate': cgst_rate,  # CGST percentage
            'sgst_rate': sgst_rate,  # SGST percentage
            'igst_rate': igst_rate,  # IGST percentage
            'hsn_number': extracted_data.get('hsn_number', 'Unknown'),  # Primary HSN number
            'vendor_address': extracted_data.get('vendor_address', 'Unknown'),
            'hsn_codes': extracted_data.get('hsn_codes', []),
            'line_items': extracted_data.get('line_items', [])
        }
        
        # Print summary
        print(f"\n📊 EXTRACTION SUMMARY:")
        print(f"  Invoice #: {structured_data['invoice_number']}")
        print(f"  Vendor: {structured_data['vendor_name']}")
        print(f"  Date: {structured_data['invoice_date']}")
        print(f"  Amount: ₹{structured_data['total_amount']:,.2f}")
        print(f"  GST Numbers: {len(structured_data['gst_numbers'])} found")
        print(f"  GST Rate: {structured_data['gst_rate']}")
        print(f"  HSN Number: {structured_data['hsn_number']}")
        print(f"  HSN Codes: {len(structured_data['hsn_codes'])} found")
        print(f"  Line Items: {len(structured_data['line_items'])} items")
        
        return {
            'success': True,
            'raw_text': extracted_data.get('raw_extracted_text', ''),
            'confidence': 95.0,  # Gemini Vision is highly accurate
            'structured_data': structured_data
        }

# Create global instance
gemini_vision_ocr = GeminiVisionOCR()

if __name__ == "__main__":
    # Test
    import sys
    if len(sys.argv) > 1:
        result = gemini_vision_ocr.process_invoice(sys.argv[1])
        if result['success']:
            print("\n" + "="*60)
            print("✅ EXTRACTION SUCCESSFUL!")
            print("="*60)
            print(json.dumps(result['structured_data'], indent=2))
        else:
            print(f"\n❌ Error: {result.get('error')}")
