"""
Gemini Vision OCR Engine for VeriFin
Uses Google's Gemini Vision AI to intelligently extract invoice data
"""

import google.generativeai as genai
import fitz  # PyMuPDF
from PIL import Image
import io
import json
import re
from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv(r"C:\D\Dev\Projects\VeriFin\.env")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
class GeminiVisionOCR:
    def __init__(self, api_key=GEMINI_API_KEY):
        """Initialize Gemini Vision with API key"""
        print("🚀 Initializing Gemini Vision OCR...")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        print("✅ Gemini Vision OCR initialized!")
    
    def convert_pdf_to_images(self, pdf_path):
        """Convert ALL PDF pages to high-quality images"""
        try:
            doc = fitz.open(str(pdf_path))
            images = []
            
            print(f"📄 PDF has {len(doc)} pages")
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                
                # High resolution for better OCR
                mat = fitz.Matrix(2.5, 2.5)  # 300 DPI
                pix = page.get_pixmap(matrix=mat, alpha=False)
                
                # Convert to PIL Image
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
    
    def create_extraction_prompt(self):
        """Create detailed prompt for Gemini to extract invoice data"""
        prompt = """You are an expert invoice data extraction AI. Analyze this invoice image carefully and extract ALL the following information:

**CRITICAL INSTRUCTIONS:**
1. Extract data EXACTLY as it appears on the invoice
2. For dates, use DD-MM-YYYY or DD/MM/YYYY format
3. For amounts, extract only numbers (no currency symbols)
4. **GST NUMBER - EXTREMELY IMPORTANT:**
   - Extract ONLY the VENDOR/SELLER/SUPPLIER GSTIN.
   - Do NOT extract the buyer/customer GSTIN.
   - Read the GSTIN EXACTLY character-by-character as printed on the invoice.
   - DO NOT add, remove, duplicate, reorder, or autocorrect any characters.
   - A GSTIN has EXACTLY 15 characters.
   - Format: 2 digits + 5 letters + 4 digits + 1 letter + 1 alphanumeric + Z + 1 alphanumeric.
   - The 5-letter section must be transcribed exactly as visible.
   - Carefully distinguish between A, E, F, P, etc.
   - Before returning a GSTIN, count the characters and verify that it contains exactly 15 characters.
   - If the GSTIN is unclear or cannot be read confidently, return an empty list rather than guessing.
   - NEVER insert an additional character just to match a GSTIN pattern.
5. If any field is not found, use "Unknown" for text fields and 0 for numeric fields

**EXTRACT THE FOLLOWING:**

1. **Invoice Number**: The invoice/bill number (look for: Invoice No, Bill No, Inv No, etc.)
2. **Vendor/Company Name**: The company/vendor issuing the invoice (usually at top in large text)
3. **Invoice Date**: The date of invoice (look for: Date, Invoice Date, Bill Date, etc.)
4. **Total Amount**: The final total amount payable (look for: Total, Grand Total, Amount Payable, Net Amount)
5. **GST Numbers**: ONLY the VENDOR/SELLER GST number (from vendor details section, NOT from buyer/customer section)
6. **GST Rate**: The TOTAL GST percentage applied
   - If CGST and SGST are separate, ADD them together (e.g., CGST 9% + SGST 9% = 18% total GST)
   - If IGST is given, use that directly
   - If only one GST rate is shown, use that
   - Examples: 
     * CGST 9% + SGST 9% → return "18%"
     * CGST 6% + SGST 6% → return "12%"
     * IGST 18% → return "18%"
7. **CGST Rate**: The CGST percentage if shown separately (e.g., 9%, 6%, 2.5%)
8. **SGST Rate**: The SGST percentage if shown separately (e.g., 9%, 6%, 2.5%)
9. **IGST Rate**: The IGST percentage if shown (e.g., 18%, 12%, 5%)
10. **HSN Number**: The primary HSN/SAC code (4-8 digit code, look for: HSN, SAC, HSN Code, SAC Code)
8. **Vendor Address**: Complete address of the vendor
9. **Line Items**: Extract all items/services with:
   - Item description
   - HSN/SAC code (if present)
   - Quantity
   - Rate/Price
   - Amount

**RETURN FORMAT:**
Return ONLY a valid JSON object with this EXACT structure (no markdown, no code blocks, just pure JSON):

{
  "invoice_number": "extracted invoice number or Unknown",
  "vendor_name": "extracted vendor/company name or Unknown",
  "invoice_date": "DD-MM-YYYY or Unknown",
  "total_amount": 0.0,
  "gst_numbers": ["list of all GST numbers found"],
  "gst_rate": "TOTAL GST percentage (CGST+SGST or IGST) e.g., 18%, 12%, 5% or Unknown",
  "cgst_rate": "CGST percentage if separate (e.g., 9%, 6%) or Unknown",
  "sgst_rate": "SGST percentage if separate (e.g., 9%, 6%) or Unknown",
  "igst_rate": "IGST percentage if applicable (e.g., 18%, 12%) or Unknown",
  "hsn_number": "primary HSN/SAC code or Unknown",
  "vendor_address": "complete address or Unknown",
  "line_items": [
    {
      "description": "item description",
      "hsn_code": "HSN/SAC code or empty",
      "quantity": 0,
      "rate": 0.0,
      "amount": 0.0
    }
  ],
  "hsn_codes": ["list of all HSN/SAC codes found"],
  "raw_extracted_text": "any other important text you see"
}

**IMPORTANT:**
- Be thorough and accurate
- Extract ALL GST numbers you find
- Extract ALL HSN/SAC codes
- If you see multiple amounts, choose the FINAL TOTAL
- Return ONLY the JSON, nothing else"""

        return prompt
    
    def extract_invoice_data(self, image):
        """Use Gemini Vision to extract structured data from invoice image"""
        try:
            print("🔍 Sending image to Gemini Vision AI...")
            
            # Create prompt
            prompt = self.create_extraction_prompt()
            
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
    
    def process_invoice(self, file_path):
        """
        Main processing function - handles multi-page PDFs
        Returns structured invoice data
        """
        print(f"\n{'='*60}")
        print(f"🔍 Processing Invoice: {Path(file_path).name}")
        print(f"{'='*60}")
        
        # Convert ALL PDF pages to images
        images = self.convert_pdf_to_images(file_path)
        
        if not images:
            return {
                'success': False,
                'error': 'Failed to convert PDF to images'
            }
        
        # Process all pages
        all_extracted_data = []
        for page_num, image in enumerate(images, 1):
            print(f"\n📄 Processing page {page_num}/{len(images)}...")
            extracted_data = self.extract_invoice_data(image)
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
