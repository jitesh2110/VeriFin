"""
GST Verification using RapidAPI
Real-time GST validation with Government data
"""

import requests
from typing import Dict, Optional
import re

#GSTIN
import os
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(env_path)
print("GST API KEY LOADED:", bool(os.getenv("GSTIN_API_KEY")))
#end

class GSTVerifier:
    def __init__(self):
        #GSTIN
        #self.api_key = "8900b371dmshae679431887f9fbfp1282bfjsn2f32a6744755"
        #self.api_host = "gst-insights-api1.p.rapidapi.com"
        #self.base_url = f"https://{self.api_host}/gstin"
        self.api_key = os.getenv("GSTIN_API_KEY")
        self.base_url = "https://www.gstinapi.in"
        #END
    
    def clean_gst_number(self, gst_number: str) -> Optional[str]:
        """
        Clean and extract valid 15-character GST from potentially malformed input
        Returns None if no valid GST found
        """
        if not gst_number:
            return None
        
        # Remove spaces and convert to uppercase
        cleaned = gst_number.replace(" ", "").upper()
        
        # If already 15 chars, return as is
        if len(cleaned) == 15:
            return cleaned
        
        # If longer than 15, try to extract valid 15-char GST
        if len(cleaned) > 15:
            # Try to find 15-char pattern in the string
            gst_pattern = r'[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}[Z]{1}[0-9A-Z]{1}'
            match = re.search(gst_pattern, cleaned)
            if match:
                extracted = match.group()
                print(f"✅ Extracted valid GST: {extracted} from {gst_number}")
                return extracted
            else:
                print(f"❌ Could not extract valid GST from: {gst_number}")
                return None
        
        # If shorter than 15, invalid
        print(f"❌ GST too short: {gst_number} ({len(cleaned)} chars)")
        return None
        
    def validate_gst_format(self, gst_number: str) -> bool:
        """Validate GST number format (MUST be EXACTLY 15 characters)"""
        if not gst_number:
            return False
        
        # Remove spaces and convert to uppercase
        gst_number = gst_number.replace(" ", "").upper()
        
        # CRITICAL: GST MUST be EXACTLY 15 characters
        if len(gst_number) != 15:
            print(f"❌ GST Length Error: {gst_number} has {len(gst_number)} chars (must be 15)")
            return False
        
        # GST format: 2 digits (state) + 10 chars (PAN) + 1 char + 1 char + 1 char
        # Pattern: 22AAAAA0000A1Z5 (exactly 15 characters)
        gst_pattern = r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}[Z]{1}[0-9A-Z]{1}$'
        
        is_valid = bool(re.match(gst_pattern, gst_number))
        
        if not is_valid:
            print(f"❌ GST Format Error: {gst_number} doesn't match pattern")
        
        return is_valid
    
    def verify_gst(self, gst_number: str) -> Dict:
        """
        Verify GST number with Government API
        Returns detailed GST information
        """
        # Clean and extract valid GST number
        cleaned_gst = self.clean_gst_number(gst_number)
        
        if not cleaned_gst:
            return {
                "success": False,
                "error": f"Invalid GST: '{gst_number}' - Must be exactly 15 characters",
                "gst_number": gst_number,
                "is_valid": False,
                "length": len(gst_number.replace(" ", ""))
            }
        
        # Validate format
        if not self.validate_gst_format(cleaned_gst):
            return {
                "success": False,
                "error": f"Invalid GST format: {cleaned_gst}",
                "gst_number": cleaned_gst,
                "is_valid": False
            }
        
        # Use cleaned GST for API call
        gst_number = cleaned_gst
        
        try:
            #GSTIN
            #  Call RapidAPI
            # url = f"{self.base_url}/{gst_number}"
            # headers = {
            #     "x-rapidapi-key": self.api_key,
            #     "x-rapidapi-host": self.api_host
            # }
            url = f"{self.base_url}/v1/gstin/{gst_number}"
            headers = {
                "x-api-key": self.api_key
            }
            #END
            
            response = requests.get(url, headers=headers, timeout=10)
            
            # Debug logging
            print(f"🔍 GST API Response for {gst_number}:")
            print(f"   Status Code: {response.status_code}")
            print(f"   Response Text: {response.text[:500]}")  # First 500 chars
            
            if response.status_code == 200:
                data = response.json()
                print(f"   Parsed Data: {data}")
                #GSTIN
                # if data.get("success"):
                #     gst_data = data.get("data", {})
                    
                #     return {
                #         "success": True,
                #         "is_valid": True,
                #         "gst_number": gst_number,
                #         "status": gst_data.get("sts", "Unknown"),
                #         "is_active": gst_data.get("sts") == "Active",
                #         "legal_name": gst_data.get("lgnm", ""),
                #         "trade_name": gst_data.get("tradeName", ""),
                #         "pan": gst_data.get("pan", ""),
                #         "address": gst_data.get("adr", ""),
                #         "pincode": gst_data.get("pincode", ""),
                #         "business_type": gst_data.get("ctb", ""),
                #         "registration_date": gst_data.get("rgdt", ""),
                #         "turnover": gst_data.get("aggreTurnOver", ""),
                #         "einvoice_status": gst_data.get("einvoiceStatus", ""),
                #         "hsn_codes": gst_data.get("hsn", []),
                #         "verification_date": None
                #     }

                if data.get("success"):
                    gst_data = data.get("data", {})

                    status = gst_data.get("status", "Unknown")
                    print(gst_data)

                    return {
                        "success": True,
                        "is_valid": True,
                        "gst_number": gst_data.get("gstin", gst_number),
                        "status": status,
                        "is_active": str(status).lower() == "active",
                        "legal_name": gst_data.get("legal_name", ""),
                        "trade_name": gst_data.get("trade_name", ""),
                        "pan": gst_data.get("pan", ""),
                        "address": gst_data.get("address", ""),
                        "pincode": gst_data.get("pincode", ""),
                        "business_type": gst_data.get("business_constitution", ""),
                        "registration_date": gst_data.get("registration_date", ""),
                        "turnover": gst_data.get("aggregate_turnover", ""),
                        "einvoice_status": gst_data.get("einvoice_status", ""),
                        "hsn_codes": gst_data.get("hsn_codes", []),
                        "verification_date": None
                    }
                #END

                
                else:
                    print(f"   ❌ API returned success=False")
                    return {
                        "success": False,
                        "is_valid": False,
                        "error": "GST not found in government database",
                        "gst_number": gst_number
                    }
            
            elif response.status_code == 404:
                print(f"   ❌ 404 - GST not found")
                return {
                    "success": False,
                    "is_valid": False,
                    "error": "GST number not found",
                    "gst_number": gst_number
                }
            
            elif response.status_code == 429:
                print(f"   ❌ 429 - Rate limit exceeded")
                return {
                    "success": False,
                    "is_valid": None,
                    "error": "API rate limit exceeded. Please try again later.",
                    "gst_number": gst_number
                }
            
            else:
                print(f"   ❌ Unexpected status code: {response.status_code}")
                return {
                    "success": False,
                    "is_valid": None,
                    "error": f"API error: {response.status_code}",
                    "gst_number": gst_number
                }
                
        except requests.Timeout:
            return {
                "success": False,
                "is_valid": None,
                "error": "API timeout. Please try again.",
                "gst_number": gst_number
            }
        except Exception as e:
            return {
                "success": False,
                "is_valid": None,
                "error": f"Verification failed: {str(e)}",
                "gst_number": gst_number
            }
    
    def check_vendor_name_match(self, gst_data: Dict, vendor_name: str) -> Dict:
        """
        Check if vendor name matches GST registered name
        """
        if not gst_data.get("success"):
            return {"match": False, "reason": "GST verification failed"}
        
        legal_name = gst_data.get("legal_name", "").lower()
        trade_name = gst_data.get("trade_name", "").lower()
        vendor_name_lower = vendor_name.lower()
        
        # Check if vendor name is in legal or trade name
        if vendor_name_lower in legal_name or legal_name in vendor_name_lower:
            return {"match": True, "matched_with": "legal_name"}
        
        if vendor_name_lower in trade_name or trade_name in vendor_name_lower:
            return {"match": True, "matched_with": "trade_name"}
        
        # Partial match (at least 50% words match)
        vendor_words = set(vendor_name_lower.split())
        legal_words = set(legal_name.split())
        
        if len(vendor_words) > 0:
            match_ratio = len(vendor_words & legal_words) / len(vendor_words)
            if match_ratio >= 0.5:
                return {"match": True, "matched_with": "partial_match", "ratio": match_ratio}
        
        return {
            "match": False,
            "reason": f"Vendor name '{vendor_name}' doesn't match GST name '{legal_name}'"
        }

# Create global instance
gst_verifier = GSTVerifier()

if __name__ == "__main__":
    # Test
    result = gst_verifier.verify_gst("18AASCA7552J1Z1")
    print("GST Verification Result:")
    import json
    print(json.dumps(result, indent=2))
