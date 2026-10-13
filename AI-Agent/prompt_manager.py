"""
VeriFin Dynamic Prompt & Tenant Configuration Engine
Loads and caches company-specific prompt rules, buyer GST exclusions,
and chat personas from external config files.
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional, List


class PromptManager:
    def __init__(self, config_dir: Optional[str] = None):
        if config_dir:
            self.config_dir = Path(config_dir)
        else:
            self.config_dir = Path(__file__).parent / "configs" / "tenants"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_mtime: Dict[str, float] = {}
        self.default_config_path = self.config_dir / "default.json"

    def get_tenant_config(self, company_id: Optional[str] = None) -> Dict[str, Any]:
        """Load tenant config file with caching and hot-reload on file change"""
        clean_id = (company_id or "comp_default").replace("/", "_").replace("\\", "_")
        tenant_file = self.config_dir / f"{clean_id}.json"

        # Check if tenant-specific file exists, otherwise use default
        target_file = tenant_file if tenant_file.exists() else self.default_config_path

        if not target_file.exists():
            # Return baseline fallback if neither exists
            return {
                "company_id": clean_id,
                "company_name": "Default Enterprise",
                "buyer_gstins": [],
                "ocr_settings": {
                    "confidence_threshold": 0.70,
                    "required_fields": ["invoice_number", "vendor_name", "total_amount", "invoice_date"],
                    "custom_extraction_rules": []
                },
                "chat_settings": {
                    "persona": "You are VeriFin, a friendly Financial Assistant."
                }
            }

        # Check cache and mtime
        file_mtime = os.path.getmtime(target_file)
        cache_key = str(target_file)

        if cache_key in self._cache and self._cache_mtime.get(cache_key) == file_mtime:
            return self._cache[cache_key]

        try:
            with open(target_file, "r", encoding="utf-8") as f:
                config_data = json.load(f)
            self._cache[cache_key] = config_data
            self._cache_mtime[cache_key] = file_mtime
            return config_data
        except Exception as e:
            print(f"⚠️ Error reading config file {target_file}: {e}")
            if cache_key in self._cache:
                return self._cache[cache_key]
            return {}

    def save_tenant_config(self, company_id: str, config_data: Dict[str, Any]) -> bool:
        """Save or update tenant configuration file"""
        clean_id = company_id.replace("/", "_").replace("\\", "_")
        tenant_file = self.config_dir / f"{clean_id}.json"
        try:
            with open(tenant_file, "w", encoding="utf-8") as f:
                json.dump(config_data, f, indent=2)
            # Invalidate cache
            cache_key = str(tenant_file)
            self._cache.pop(cache_key, None)
            return True
        except Exception as e:
            print(f"❌ Failed to save tenant config for {company_id}: {e}")
            return False

    def build_extraction_prompt(self, company_id: Optional[str] = None) -> str:
        """Build company-tailored Gemini extraction prompt"""
        config = self.get_tenant_config(company_id)
        company_name = config.get("company_name", "Default Enterprise")
        buyer_gstins = config.get("buyer_gstins", [])
        ocr_settings = config.get("ocr_settings", {})
        custom_rules = ocr_settings.get("custom_extraction_rules", [])

        # Build buyer GST exclusion block
        buyer_gst_block = ""
        if buyer_gstins:
            gst_list_str = ", ".join(buyer_gstins)
            buyer_gst_block = f"""
**CRITICAL BUYER/CLIENT EXCLUSION FOR {company_name.upper()}:**
The following GSTIN(s) belong to the BUYER ({company_name}): [{gst_list_str}]
- NEVER return any of these as the vendor/seller GSTIN!
- Look specifically for the COUNTERPARTY/VENDOR/SUPPLIER GSTIN that is distinct from [{gst_list_str}].
"""

        custom_rules_block = ""
        if custom_rules:
            rules_bullets = "\n".join(f"- {rule}" for rule in custom_rules)
            custom_rules_block = f"""
**COMPANY-SPECIFIC EXTRACTION RULES ({company_name}):**
{rules_bullets}
"""

        prompt = f"""You are an expert invoice data extraction AI customized for {company_name}.
Analyze this invoice image carefully and extract ALL relevant financial and compliance information.

{buyer_gst_block}
{custom_rules_block}

**CRITICAL INSTRUCTIONS:**
1. Extract data EXACTLY as it appears on the invoice.
2. For dates, standardize to DD-MM-YYYY or DD/MM/YYYY.
3. For amounts, extract only numeric values without currency symbols.
4. **GST NUMBER - EXTREMELY IMPORTANT:**
   - Extract ONLY the VENDOR / SELLER / SUPPLIER GSTIN.
   - Do NOT extract the buyer / recipient GSTIN.
   - Read the GSTIN EXACTLY character-by-character as printed (15 characters: 2 digits + 5 letters + 4 digits + 1 letter + 1 alphanumeric + Z + 1 alphanumeric).
   - If GSTIN cannot be determined with certainty, return an empty list rather than guessing.
5. If any field is not found, use "Unknown" for text fields and 0 for numeric fields.

**EXTRACT THE FOLLOWING FIELDS:**
1. **Invoice Number**: The invoice/bill number.
2. **Vendor Name**: The business issuing the invoice.
3. **Invoice Date**: Date of the invoice.
4. **Total Amount**: Final grand total payable.
5. **GST Numbers**: ONLY the vendor GST numbers.
6. **GST Rate**: Total GST % applied (CGST+SGST or IGST).
7. **CGST Rate / SGST Rate / IGST Rate**: Individual rates if specified.
8. **HSN Number**: Primary HSN/SAC code.
9. **Vendor Address**: Address of the vendor.
10. **Line Items**: List of items/services with:
    - description: Item name
    - hsn_code: HSN/SAC code (if visible)
    - quantity: Numeric quantity
    - rate: Unit price
    - amount: Total item amount

**RETURN FORMAT:**
Return ONLY a valid JSON object with this EXACT structure (no markdown fences, just pure JSON):

{{
  "invoice_number": "extracted invoice number or Unknown",
  "vendor_name": "extracted vendor name or Unknown",
  "invoice_date": "DD-MM-YYYY or Unknown",
  "total_amount": 0.0,
  "gst_numbers": ["list of vendor GST numbers found"],
  "gst_rate": "TOTAL GST percentage (e.g. 18%, 12%, 5% or Unknown)",
  "cgst_rate": "CGST rate or Unknown",
  "sgst_rate": "SGST rate or Unknown",
  "igst_rate": "IGST rate or Unknown",
  "hsn_number": "primary HSN code or Unknown",
  "vendor_address": "vendor address or Unknown",
  "line_items": [
    {{
      "description": "item description",
      "hsn_code": "HSN/SAC code or empty",
      "quantity": 0,
      "rate": 0.0,
      "amount": 0.0
    }}
  ],
  "hsn_codes": ["list of all HSN codes found"],
  "raw_extracted_text": "additional text summary"
}}
"""
        return prompt

    def build_chat_system_prompt(
        self,
        company_id: Optional[str],
        stats: Dict[str, Any],
        invoices: List[Dict[str, Any]],
        vendors: List[Dict[str, Any]],
        anomalies: List[Dict[str, Any]],
        user_message: str
    ) -> str:
        """Build company-tailored Gemini Chatbot prompt"""
        config = self.get_tenant_config(company_id)
        company_name = config.get("company_name", "Default Enterprise")
        chat_settings = config.get("chat_settings", {})
        persona = chat_settings.get("persona", f"You are VeriFin, a friendly Financial Assistant for {company_name}.")

        prompt = f"""{persona}
You are operating within the context of {company_name}. Answer questions about invoices and expenses in simple, clear language.

IMPORTANT RULES:
1. DO NOT use markdown formatting (no **, *, #, etc.)
2. Use simple, conversational language
3. Keep responses short and to the point (2-3 sentences max)
4. Use plain text only, no special formatting
5. Speak like you are talking to a business executive or finance manager

Current Company Data ({company_name}):
- Total Invoices: {stats.get('totalInvoices', 0)}
- Total Vendors: {stats.get('totalVendors', 0)}
- Total Anomalies: {stats.get('totalAnomalies', 0)}
- Total Amount Processed: ₹{stats.get('totalAmountProcessed', 0):,.2f}

Recent Invoices:
{json.dumps(invoices[:3], indent=2, default=str)}

Vendors:
{json.dumps(vendors[:3], indent=2, default=str)}

Anomalies:
{json.dumps(anomalies[:3], indent=2, default=str)}

User Question: {user_message}

Answer in simple, plain English without any markdown or technical jargon. Be brief and helpful."""
        return prompt


# Singleton instance
prompt_manager = PromptManager()
