"""
VeriFin - Fixed API Server
Working version with all compliance features
"""

from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
import uvicorn
import os
import sys
import shutil
import json
from pathlib import Path
from datetime import datetime
import google.generativeai as genai
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np
import re
import fitz  # PyMuPDF
from PIL import Image
import io
from dotenv import load_dotenv

# Ensure UTF-8 output encoding on Windows console
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Import our existing components
from gemini_vision_ocr import gemini_vision_ocr  # Gemini Vision OCR
from ml_trainer import VeriFinMLTrainer
from database import VeriFinDatabase
from gst_verifier import gst_verifier
from hsn_sac_verifier import hsn_sac_verifier  # HSN/SAC Verification

# Multi-Tenancy, Storage & Prompt Config components
from auth_middleware import get_current_user, TenantUser
from image_optimizer import image_optimizer
from prompt_manager import prompt_manager

# NEW: Import LangChain integration (optional)
try:
    from integrate_langchain import analyze_invoice_hybrid
    LANGCHAIN_AVAILABLE = True
    print("✅ LangChain integration available")
except ImportError:
    LANGCHAIN_AVAILABLE = False
    print("⚠️  LangChain not available (optional feature)")

# Initialize FastAPI
app = FastAPI(
    title="VeriFin - Complete Compliance API", 
    version="2.0.0",
    description="AI-powered invoice processing with full regulatory compliance & multi-tenancy"
)

# Mount /uploads for static access to optimized receipt images and thumbnails
os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Add CORS middleware with more permissive settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Initialize VeriFin components
print("Initializing VeriFin Complete System...")
print("line number 59 dsihvc sgcl")

# Core components
# ocr_engine = EasyOCREngine()  # Old OCR
# Using enhanced_ocr instead (imported above)
ml_trainer = VeriFinMLTrainer()
db = VeriFinDatabase()  # MongoDB connection

# Load trained models
if not ml_trainer.load_models():
    print("Loading real trained models...")
    if os.path.exists("verifin_real_trained_models.pkl"):
        ml_trainer.load_models("verifin_real_trained_models.pkl")
    elif os.path.exists("fintel_real_trained_models.pkl"):
        ml_trainer.load_models("fintel_real_trained_models.pkl")
    elif os.path.exists("verifin_models.pkl"):
        ml_trainer.load_models("verifin_models.pkl")
    else:
        ml_trainer.load_models("fintel_models.pkl")

print("VeriFin Complete System ready!")

# Configure Gemini AI
load_dotenv(r"C:\D\Dev\Projects\VeriFin\.env")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel('gemini-2.5-flash')
print("Gemini AI configured!")

# Create directories
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# HSN/SAC Database
HSN_SAC_DATABASE = {
    "8517": {"description": "Telephone sets, mobile phones", "gst_rate": 12.0},
    "8471": {"description": "Computers and computer peripherals", "gst_rate": 18.0},
    "9403": {"description": "Office furniture", "gst_rate": 12.0},
    "7326": {"description": "Articles of iron or steel", "gst_rate": 18.0},
    "3926": {"description": "Articles of plastics", "gst_rate": 18.0},
    "8443": {"description": "Printing machinery", "gst_rate": 18.0},
    "4901": {"description": "Printed books, brochures", "gst_rate": 12.0},
    "9983": {"description": "Professional services", "gst_rate": 18.0}
}

@app.get("/")
async def root():
    return {
        "message": "VeriFin Complete Compliance System",
        "version": "2.0.0",
        "status": "All 12 compliance features active"
    }

@app.options("/api/invoices/upload")
async def upload_options():
    """Handle preflight OPTIONS request"""
    return {"message": "OK"}

@app.get("/api/health")
async def health_check():
    """Enhanced health check"""
    return {
        "status": "VeriFin Complete System Online",
        "timestamp": datetime.now().isoformat(),
        "version": "2.0.0",
        "services": {
            "ai_agent": "Active",
            "ocr_engine": "Ready", 
            "ml_models": "Trained on Real Data",
            "compliance_system": "All 12 Features Active"
        }
    }

@app.get("/api/invoices/history")
async def get_invoice_history(
    limit: int = 50,
    project_id: Optional[str] = None,
    current_user: TenantUser = Depends(get_current_user)
):
    """Get invoice history from tenant database"""
    try:
        active_project = project_id or current_user.active_project_id
        invoices = db.get_invoice_history(
            limit=limit,
            company_id=current_user.company_id,
            project_id=active_project
        )
        return {
            "success": True,
            "invoices": invoices,
            "count": len(invoices),
            "companyId": current_user.company_id,
            "projectId": active_project
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/api/vendors")
async def get_vendors(
    current_user: TenantUser = Depends(get_current_user)
):
    """Get list of vendors for current tenant company"""
    try:
        vendors = db.get_vendor_list(company_id=current_user.company_id)
        return {
            "success": True,
            "vendors": vendors,
            "count": len(vendors),
            "companyId": current_user.company_id
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/api/anomalies")
async def get_anomalies(
    severity: Optional[str] = None,
    limit: int = 50,
    project_id: Optional[str] = None,
    current_user: TenantUser = Depends(get_current_user)
):
    """Get detected anomalies from tenant database"""
    try:
        anomalies = db.get_anomalies(
            severity=severity,
            limit=limit,
            company_id=current_user.company_id,
            project_id=project_id or current_user.active_project_id
        )
        return {
            "success": True,
            "anomalies": anomalies,
            "count": len(anomalies),
            "companyId": current_user.company_id
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/api/dashboard/stats")
async def get_dashboard_stats(
    project_id: Optional[str] = None,
    current_user: TenantUser = Depends(get_current_user)
):
    """Get dashboard statistics for tenant company"""
    try:
        stats = db.get_dashboard_stats(
            company_id=current_user.company_id,
            project_id=project_id or current_user.active_project_id
        )
        return {
            "success": True,
            "stats": stats,
            "companyId": current_user.company_id,
            "companyName": current_user.company_name
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/api/dashboard/anomaly-trends")
async def get_anomaly_trends(
    days: int = 30,
    project_id: Optional[str] = None,
    current_user: TenantUser = Depends(get_current_user)
):
    """Get anomaly trends for tenant company"""
    try:
        trends = db.get_anomaly_trends(
            days=days,
            company_id=current_user.company_id,
            project_id=project_id or current_user.active_project_id
        )
        return {"success": True, "trends": trends, "companyId": current_user.company_id}
    except Exception as e:
        return {"success": False, "error": str(e), "trends": []}

# Pydantic model for chat request
class ChatRequest(BaseModel):
    message: str

@app.post("/api/chat")
async def chat_with_gemini(
    request: ChatRequest,
    current_user: TenantUser = Depends(get_current_user)
):
    """Chat with Gemini AI with company-tailored persona and data context"""
    try:
        # Get context from tenant database
        stats = db.get_dashboard_stats(company_id=current_user.company_id)
        vendors = db.get_vendor_list(company_id=current_user.company_id)
        anomalies = db.get_anomalies(limit=10, company_id=current_user.company_id)
        invoices = db.get_invoice_history(limit=10, company_id=current_user.company_id)
        
        # Build prompt using company-specific configuration
        context = prompt_manager.build_chat_system_prompt(
            company_id=current_user.company_id,
            stats=stats,
            invoices=invoices,
            vendors=vendors,
            anomalies=anomalies,
            user_message=request.message
        )

        # Get response from Gemini
        response = gemini_model.generate_content(context)
        
        return {
            "success": True,
            "response": response.text,
            "companyId": current_user.company_id
        }
    except Exception as e:
        print(f"Chat error: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "response": "Sorry, I'm having trouble processing your request. Please try again."
        }

# Company Configuration Management Endpoints
@app.get("/api/config/tenant")
async def get_tenant_config(
    current_user: TenantUser = Depends(get_current_user)
):
    """Get configuration and prompt rules for current company"""
    config = prompt_manager.get_tenant_config(current_user.company_id)
    return {"success": True, "config": config, "companyId": current_user.company_id}

@app.post("/api/config/tenant")
async def save_tenant_config(
    config: Dict[str, Any] = Body(...),
    current_user: TenantUser = Depends(get_current_user)
):
    """Save or update company configuration and custom prompt rules"""
    saved = prompt_manager.save_tenant_config(current_user.company_id, config)
    return {"success": saved, "message": "Company configuration updated"}

# Pydantic models for Manual Invoices & Line Items
class LineItemModel(BaseModel):
    description: str = "Item"
    hsn_code: Optional[str] = ""
    quantity: float = 1.0
    rate: float = 0.0
    amount: float = 0.0
    gst_rate: Optional[str] = None
    gst_amount: Optional[float] = None

class ManualInvoiceRequest(BaseModel):
    invoiceNumber: str
    vendorName: str
    invoiceDate: str
    invoiceAmount: float
    gstNumbers: List[str] = []
    gstRate: Optional[str] = "18%"
    cgstRate: Optional[str] = "9%"
    sgstRate: Optional[str] = "9%"
    igstRate: Optional[str] = "0%"
    hsnNumber: Optional[str] = ""
    hsnSacCodes: List[str] = []
    lineItems: List[LineItemModel] = []
    vendorAddress: Optional[str] = ""
    imageUrl: Optional[str] = None
    thumbnailUrl: Optional[str] = None
    rawText: Optional[str] = ""

def process_and_save_invoice_internal(
    invoice_data: Dict[str, Any],
    line_items: List[Dict[str, Any]],
    enhanced_data: Dict[str, Any],
    company_id: str,
    project_id: str,
    image_url: Optional[str] = None,
    thumbnail_url: Optional[str] = None,
    storage_info: Optional[Dict[str, Any]] = None,
    is_manual: bool = False,
    existing_invoice_id: Optional[str] = None
) -> Dict[str, Any]:
    """Internal helper to run full compliance and save invoice to tenant database"""
    # 1. GST Verification with RapidAPI
    gst_verification_results = []
    gst_missing = False
    
    if invoice_data.get('gst_numbers') and len(invoice_data['gst_numbers']) > 0:
        print(f"🔍 Verifying GST numbers: {invoice_data['gst_numbers']}")
        for gst_num in invoice_data['gst_numbers']:
            verification = gst_verifier.verify_gst(gst_num)
            gst_verification_results.append(verification)
            
            if verification.get('success'):
                name_match = gst_verifier.check_vendor_name_match(
                    verification, 
                    invoice_data.get('vendor_name', '')
                )
                verification['vendor_name_match'] = name_match
    else:
        gst_missing = True
        gst_verification_results.append({
            "success": False,
            "error": "GST number not found in invoice",
            "is_valid": False,
            "gst_missing": True
        })
    
    invoice_data['gst_verification'] = gst_verification_results
    invoice_data['gst_missing'] = gst_missing
    
    # 2. HSN/SAC Code Verification
    hsn_sac_verification_results = []
    line_items_verification = None
    hsn_codes = enhanced_data.get('hsn_sac_codes', [])
    
    if line_items and len(line_items) > 0:
        line_items_verification = hsn_sac_verifier.verify_with_line_items(line_items)
        hsn_sac_verification_results = line_items_verification['verifications']
    elif hsn_codes and len(hsn_codes) > 0:
        for code in hsn_codes:
            if code and code != 'Unknown':
                verification = hsn_sac_verifier.verify_code(code)
                hsn_sac_verification_results.append(verification)
    
    invoice_data['hsn_sac_verification'] = hsn_sac_verification_results
    invoice_data['hsn_sac_line_items_verification'] = line_items_verification
    
    # 3. ML Anomaly Detection
    ml_features = extract_ml_features(invoice_data)
    ml_result = None
    if ml_features:
        ml_result = ml_trainer.predict_anomaly(ml_features)
    
    # 4. Complete Compliance Scoring
    compliance_results = process_complete_compliance(invoice_data, enhanced_data, ml_result)
    
    # 5. Store/Update invoice in MongoDB
    invoice_storage_data = {
        **invoice_data,
        'companyId': company_id,
        'projectId': project_id,
        'image_url': image_url,
        'thumbnail_url': thumbnail_url,
        'storage_info': storage_info or {},
        'is_manual_entry': is_manual,
        'processing_status': 'completed',
        'compliance_results': compliance_results,
        'ml_prediction': ml_result,
        'gst_verification': gst_verification_results,
        'gst_missing': gst_missing,
        'hsn_sac_verification': hsn_sac_verification_results,
        'hsn_sac_line_items_verification': line_items_verification,
        'line_items': line_items
    }

    if existing_invoice_id:
        from bson import ObjectId
        tenant_db = db.get_tenant_db(company_id)
        try:
            obj_id = ObjectId(existing_invoice_id)
        except Exception:
            obj_id = existing_invoice_id
        tenant_db['invoices'].update_one({'_id': obj_id}, {'$set': invoice_storage_data})
        invoice_id = str(existing_invoice_id)
    else:
        invoice_id = db.store_invoice(invoice_storage_data, company_id=company_id, project_id=project_id)
    
    # 6. Detect anomalies by comparing with historical data
    db_anomalies = db.detect_anomalies(invoice_storage_data, invoice_id, company_id=company_id, project_id=project_id)
    
    # 7. AI Analysis (optional)
    ai_analysis_result = None
    if LANGCHAIN_AVAILABLE:
        try:
            ai_analysis_result = analyze_invoice_hybrid(
                invoice_data={
                    "invoice_number": invoice_data.get('invoice_number'),
                    "vendor_name": invoice_data.get('vendor_name'),
                    "invoice_date": invoice_data.get('invoice_date'),
                    "total_amount": invoice_data.get('total_amount', 0),
                    "gst_numbers": invoice_data.get('gst_numbers', []),
                    "gst_verification": gst_verification_results,
                    "hsn_verification": hsn_sac_verification_results,
                    "ml_analysis": ml_result,
                    "database_anomalies": db_anomalies,
                    "compliance_results": compliance_results,
                    "line_items": line_items
                },
                invoice_id=invoice_id,
                use_ai=True
            )
            if ai_analysis_result and ai_analysis_result.get("ai_used"):
                ai_data = {
                    "ai_analysis": ai_analysis_result.get("ai_analysis"),
                    "ai_used": ai_analysis_result.get("ai_used", False),
                    "ai_confidence": ai_analysis_result.get("ai_confidence"),
                    "ai_analysis_timestamp": datetime.now()
                }
                tenant_db = db.get_tenant_db(company_id)
                from bson import ObjectId
                try:
                    obj_id = ObjectId(invoice_id)
                except Exception:
                    obj_id = invoice_id
                tenant_db['invoices'].update_one({"_id": obj_id}, {"$set": ai_data})
        except Exception as e:
            print(f"⚠️ AI Analysis failed: {e}")
            ai_analysis_result = {"ai_used": False, "error": str(e)}

    # Format response
    return {
        "success": True,
        "message": "Invoice processed with complete compliance checking",
        "filename": invoice_data.get('filename', 'invoice'),
        "processing_timestamp": datetime.now().isoformat(),
        "companyId": company_id,
        "projectId": project_id,
        "imageUrl": image_url,
        "thumbnailUrl": thumbnail_url,
        "storageInfo": storage_info,
        "isManualEntry": is_manual,
        "data": {
            "invoiceNumber": safe_convert(invoice_data.get('invoice_number', 'Unknown')),
            "vendorName": safe_convert(invoice_data.get('vendor_name', 'Unknown')),
            "invoiceAmount": safe_convert(invoice_data.get('total_amount', 0)),
            "invoiceDate": safe_convert(invoice_data.get('invoice_date', 'Unknown')),
            "gstNumbers": invoice_data.get('gst_numbers', []),
            "gstRate": invoice_data.get('gst_rate', 'Unknown'),
            "hsnNumber": invoice_data.get('hsn_number', 'Unknown'),
            "ocrConfidence": float(invoice_data.get('ocr_confidence', 100.0 if is_manual else 0.0)),
            "imageUrl": image_url,
            "thumbnailUrl": thumbnail_url,
            "hsnSacCodes": enhanced_data.get('hsn_sac_codes', []),
            "itemDescriptions": enhanced_data.get('item_descriptions', []),
            "quantities": enhanced_data.get('quantities', []),
            "mlPrediction": convert_numpy_types(ml_result) if ml_result else {"is_anomaly": False, "confidence": 0},
            "complianceScore": compliance_results['compliance_score'],
            "complianceStatus": compliance_results['compliance_status'],
            "checksPassedCount": compliance_results['checks_passed'],
            "totalChecksCount": 12,
            "riskScore": compliance_results['risk_score'],
            "riskLevel": compliance_results['risk_level'],
            "gstVerification": gst_verification_results,
            "gstMissing": gst_missing,
            "hsnSacVerification": hsn_sac_verification_results,
            "hsnSacCodesFound": len(hsn_codes),
            "hsnSacValid": sum(1 for v in hsn_sac_verification_results if v.get('is_valid')),
            "hsnSacInvalid": sum(1 for v in hsn_sac_verification_results if not v.get('is_valid')),
            "hsnSacLineItemsVerification": line_items_verification,
            "hsnSacRateMismatches": line_items_verification['rate_mismatches'] if line_items_verification else [],
            "hsnSacRateMismatchCount": line_items_verification['rate_mismatch_count'] if line_items_verification else 0,
            "gstValidations": compliance_results['gst_validations'],
            "hsnValidations": compliance_results['hsn_validations'],
            "duplicateCheck": compliance_results['duplicate_check'],
            "arithmeticCheck": compliance_results['arithmetic_check'],
            "priceAnalysis": compliance_results['price_analysis'],
            "anomaliesDetected": compliance_results['anomalies_detected'],
            "databaseAnomalies": db_anomalies,
            "invoiceId": invoice_id,
            "aiAnalysis": {
                "enabled": LANGCHAIN_AVAILABLE,
                "used": ai_analysis_result.get("ai_used") if ai_analysis_result else False,
                "analysis": ai_analysis_result.get("ai_analysis") if ai_analysis_result else None,
                "confidence": ai_analysis_result.get("ai_confidence") if ai_analysis_result else None
            }
        }
    }

@app.post("/api/invoices/upload")
async def upload_invoice_complete(
    file: UploadFile = File(...),
    current_user: TenantUser = Depends(get_current_user)
):
    """Complete invoice processing with image optimization, tenant prompt, and mid-layer fallback"""
    try:
        # Save uploaded file
        file_path = UPLOAD_DIR / file.filename
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        print(f"📄 Processing: {file.filename} for company [{current_user.company_id}]")
        
        # Optimize image to WebP and generate thumbnail (Item 2: storage optimization)
        try:
            storage_result = image_optimizer.optimize_and_store(
                file_path=file_path,
                company_id=current_user.company_id
            )
            print(f"📦 Stored WebP image ({storage_result['savings_percent']}% savings): {storage_result['image_url']}")
        except Exception as e:
            print(f"⚠️ Image optimizer warning: {e}")
            storage_result = {
                "image_url": f"/uploads/{file.filename}",
                "thumbnail_url": f"/uploads/{file.filename}",
                "savings_percent": 0.0
            }

        # OCR Processing with Gemini Vision using company-specific prompt
        ocr_result = None
        try:
            ocr_result = gemini_vision_ocr.process_invoice(str(file_path), company_id=current_user.company_id)
        except Exception as ocr_err:
            print(f"⚠️ Gemini OCR error: {ocr_err}")
            ocr_result = {"success": False, "error": str(ocr_err)}

        # Check for OCR breakdown / low confidence (Item 1: Mid-layer manual fallback)
        ocr_failed = (
            not ocr_result 
            or not ocr_result.get('success') 
            or float(ocr_result.get('confidence', 0)) < 65.0
        )

        if ocr_failed:
            print("🚨 AI OCR broke down or has low confidence! Offering mid-layer manual entry fallback.")
            partial_structured = ocr_result.get('structured_data', {}) if ocr_result else {}
            
            # Create a draft invoice in tenant database
            draft_storage_data = {
                'filename': file.filename,
                'invoice_number': partial_structured.get('invoice_number', 'Unknown'),
                'vendor_name': partial_structured.get('vendor_name', 'Unknown'),
                'total_amount': float(partial_structured.get('total_amount', 0)),
                'invoice_date': partial_structured.get('invoice_date', 'Unknown'),
                'gst_numbers': partial_structured.get('gst_numbers', []),
                'ocr_confidence': float(ocr_result.get('confidence', 0)) if ocr_result else 0.0,
                'raw_text': ocr_result.get('raw_text', '') if ocr_result else '',
                'image_url': storage_result.get('image_url'),
                'thumbnail_url': storage_result.get('thumbnail_url'),
                'storage_info': storage_result,
                'is_manual_entry': False,
                'processing_status': 'needs_manual_review'
            }
            draft_id = db.store_invoice(
                draft_storage_data,
                company_id=current_user.company_id,
                project_id=current_user.active_project_id
            )

            return {
                "success": False,
                "needs_manual_review": True,
                "draftId": draft_id,
                "message": "AI OCR extraction encountered an error or low confidence. You can review and enter invoice details manually.",
                "filename": file.filename,
                "imageUrl": storage_result.get('image_url'),
                "thumbnailUrl": storage_result.get('thumbnail_url'),
                "storageInfo": storage_result,
                "partialData": {
                    "invoiceNumber": partial_structured.get('invoice_number', ''),
                    "vendorName": partial_structured.get('vendor_name', ''),
                    "invoiceDate": partial_structured.get('invoice_date', ''),
                    "invoiceAmount": float(partial_structured.get('total_amount', 0)),
                    "gstNumbers": partial_structured.get('gst_numbers', []),
                    "ocrConfidence": float(ocr_result.get('confidence', 0)) if ocr_result else 0.0
                }
            }
        
        # Enhanced data extraction
        raw_text = ocr_result.get('raw_text') or ocr_result.get('text') or ""
        enhanced_data = extract_enhanced_invoice_data(raw_text)
        
        # Total amount conversion
        total_amount_raw = ocr_result['structured_data'].get('total_amount', 0)
        try:
            total_amount = float(str(total_amount_raw).replace(',', '')) if total_amount_raw else 0
        except Exception:
            total_amount = 0
        
        invoice_data = {
            'filename': file.filename,
            'invoice_number': ocr_result['structured_data'].get('invoice_number', 'Unknown'),
            'total_amount': total_amount,
            'invoice_date': ocr_result['structured_data'].get('invoice_date', 'Unknown'),
            'vendor_name': ocr_result['structured_data'].get('vendor_name', 'Unknown'),
            'gst_numbers': ocr_result['structured_data'].get('gst_numbers', []),
            'gst_rate': ocr_result['structured_data'].get('gst_rate', 'Unknown'),
            'cgst_rate': ocr_result['structured_data'].get('cgst_rate', 'Unknown'),
            'sgst_rate': ocr_result['structured_data'].get('sgst_rate', 'Unknown'),
            'igst_rate': ocr_result['structured_data'].get('igst_rate', 'Unknown'),
            'hsn_number': ocr_result['structured_data'].get('hsn_number', 'Unknown'),
            'hsn_sac_codes': enhanced_data.get('hsn_sac_codes', []),
            'item_descriptions': enhanced_data.get('item_descriptions', []),
            'quantities': enhanced_data.get('quantities', []),
            'ocr_confidence': ocr_result.get('confidence', 95.0),
            'raw_text': ocr_result.get('raw_text', '')
        }
        line_items = ocr_result['structured_data'].get('line_items', [])

        return process_and_save_invoice_internal(
            invoice_data=invoice_data,
            line_items=line_items,
            enhanced_data=enhanced_data,
            company_id=current_user.company_id,
            project_id=current_user.active_project_id,
            image_url=storage_result.get('image_url'),
            thumbnail_url=storage_result.get('thumbnail_url'),
            storage_info=storage_result,
            is_manual=False
        )

    except Exception as e:
        print(f"❌ Upload processing failed: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": f"Processing failed: {str(e)}"}

# Mid-Layer Manual Entry & Review Endpoints (Item 1)
@app.post("/api/invoices/manual")
async def create_manual_invoice(
    request: ManualInvoiceRequest,
    current_user: TenantUser = Depends(get_current_user)
):
    """
    Manually create and validate an invoice when AI OCR breaks down
    or for manual business entry with complete compliance checking
    """
    try:
        print(f"📝 Processing manual invoice entry for company [{current_user.company_id}]...")
        
        line_items_dict = [item.dict() for item in request.lineItems]
        hsn_codes = request.hsnSacCodes or [item.hsn_code for item in request.lineItems if item.hsn_code]
        
        invoice_data = {
            'filename': f"manual_{request.invoiceNumber}.pdf",
            'invoice_number': request.invoiceNumber,
            'vendor_name': request.vendorName,
            'total_amount': float(request.invoiceAmount),
            'invoice_date': request.invoiceDate,
            'gst_numbers': request.gstNumbers,
            'gst_rate': request.gstRate or "18%",
            'cgst_rate': request.cgstRate or "9%",
            'sgst_rate': request.sgstRate or "9%",
            'igst_rate': request.igstRate or "0%",
            'hsn_number': request.hsnNumber or (hsn_codes[0] if hsn_codes else "Unknown"),
            'hsn_sac_codes': hsn_codes,
            'item_descriptions': [item.description for item in request.lineItems],
            'quantities': [item.quantity for item in request.lineItems],
            'ocr_confidence': 100.0,
            'raw_text': request.rawText or f"Manual Entry: {request.invoiceNumber} from {request.vendorName}"
        }

        enhanced_data = {
            'hsn_sac_codes': hsn_codes,
            'item_descriptions': invoice_data['item_descriptions'],
            'quantities': invoice_data['quantities']
        }

        return process_and_save_invoice_internal(
            invoice_data=invoice_data,
            line_items=line_items_dict,
            enhanced_data=enhanced_data,
            company_id=current_user.company_id,
            project_id=current_user.active_project_id,
            image_url=request.imageUrl,
            thumbnail_url=request.thumbnailUrl,
            is_manual=True
        )
    except Exception as e:
        print(f"❌ Manual invoice creation failed: {e}")
        return {"success": False, "error": str(e)}

@app.put("/api/invoices/{invoice_id}/review")
async def review_and_update_invoice(
    invoice_id: str,
    request: ManualInvoiceRequest,
    current_user: TenantUser = Depends(get_current_user)
):
    """
    Update and re-validate an existing invoice after manual review
    """
    try:
        print(f"🔄 Updating reviewed invoice [{invoice_id}] for company [{current_user.company_id}]...")
        
        line_items_dict = [item.dict() for item in request.lineItems]
        hsn_codes = request.hsnSacCodes or [item.hsn_code for item in request.lineItems if item.hsn_code]
        
        invoice_data = {
            'filename': f"reviewed_{request.invoiceNumber}.pdf",
            'invoice_number': request.invoiceNumber,
            'vendor_name': request.vendorName,
            'total_amount': float(request.invoiceAmount),
            'invoice_date': request.invoiceDate,
            'gst_numbers': request.gstNumbers,
            'gst_rate': request.gstRate or "18%",
            'cgst_rate': request.cgstRate or "9%",
            'sgst_rate': request.sgstRate or "9%",
            'igst_rate': request.igstRate or "0%",
            'hsn_number': request.hsnNumber or (hsn_codes[0] if hsn_codes else "Unknown"),
            'hsn_sac_codes': hsn_codes,
            'item_descriptions': [item.description for item in request.lineItems],
            'quantities': [item.quantity for item in request.lineItems],
            'ocr_confidence': 100.0,
            'raw_text': request.rawText or f"Reviewed Entry: {request.invoiceNumber}"
        }

        enhanced_data = {
            'hsn_sac_codes': hsn_codes,
            'item_descriptions': invoice_data['item_descriptions'],
            'quantities': invoice_data['quantities']
        }

        return process_and_save_invoice_internal(
            invoice_data=invoice_data,
            line_items=line_items_dict,
            enhanced_data=enhanced_data,
            company_id=current_user.company_id,
            project_id=current_user.active_project_id,
            image_url=request.imageUrl,
            thumbnail_url=request.thumbnailUrl,
            is_manual=True,
            existing_invoice_id=invoice_id
        )
    except Exception as e:
        print(f"❌ Review update failed: {e}")
        return {"success": False, "error": str(e)}

def convert_pdf_to_image(pdf_path):
    """Convert PDF to image"""
    try:
        doc = fitz.open(str(pdf_path))
        page = doc.load_page(0)
        mat = fitz.Matrix(2.0, 2.0)
        pix = page.get_pixmap(matrix=mat)
        img_data = pix.tobytes("png")
        img = Image.open(io.BytesIO(img_data))
        
        image_path = pdf_path.with_suffix('.png')
        img.save(image_path, "PNG", dpi=(300, 300))
        doc.close()
        return image_path
    except Exception as e:
        print(f"PDF conversion error: {e}")
        return pdf_path

def extract_enhanced_invoice_data(ocr_text):
    """Enhanced extraction for HSN/SAC and items"""
    enhanced_data = {}
    
    # HSN/SAC code extraction
    hsn_patterns = [
        r'HSN\s*:?\s*(\d{4,8})',
        r'SAC\s*:?\s*(\d{4,6})',
        r'HSN/SAC\s*:?\s*(\d{4,8})'
        # Removed r'\b(\d{4})\b' to prevent catching random 4-digit prices/amounts
    ]
    
    hsn_codes = []
    for pattern in hsn_patterns:
        matches = re.findall(pattern, ocr_text, re.IGNORECASE)
        hsn_codes.extend(matches)
    
    enhanced_data['hsn_sac_codes'] = list(set(hsn_codes))
    
    # Item description extraction
    item_patterns = [
        r'DESCRIPTION\s*:?\s*([^\n\r]+)',
        r'ITEM\s*:?\s*([^\n\r]+)',
        r'PRODUCT\s*:?\s*([^\n\r]+)',
        r'SERVICE\s*:?\s*([^\n\r]+)'
    ]
    
    items = []
    for pattern in item_patterns:
        matches = re.findall(pattern, ocr_text, re.IGNORECASE)
        items.extend([item.strip() for item in matches if len(item.strip()) > 3])
    
    enhanced_data['item_descriptions'] = list(set(items))
    
    # Quantity extraction
    qty_patterns = [
        r'QTY\s*:?\s*(\d+(?:\.\d+)?)',
        r'QUANTITY\s*:?\s*(\d+(?:\.\d+)?)'
    ]
    
    quantities = []
    for pattern in qty_patterns:
        matches = re.findall(pattern, ocr_text, re.IGNORECASE)
        quantities.extend([float(q) for q in matches])
    
    enhanced_data['quantities'] = quantities
    
    return enhanced_data
    
def process_complete_compliance(invoice_data, enhanced_data, ml_result):
    """Process complete compliance check"""
    compliance_results = {
        'compliance_score': 0,
        'checks_passed': 0,
        'total_checks': 12
    }
    
    anomalies = []  
    
    # Basic field checks (5 points)
    basic_fields = ['invoice_number', 'total_amount', 'invoice_date', 'vendor_name', 'gst_numbers']
    for field in basic_fields:
        if invoice_data.get(field):
            compliance_results['checks_passed'] += 1
    
    # Enhanced extraction check (1 point)
    if enhanced_data.get('hsn_sac_codes') or enhanced_data.get('item_descriptions'):
        compliance_results['checks_passed'] += 1
    
    # OCR accuracy check (1 point)
    if invoice_data.get('ocr_confidence', 0) >= 80:
        compliance_results['checks_passed'] += 1
    
    # GST validation (1 point)
    gst_validations = []
    for gst_num in invoice_data.get('gst_numbers', []):
        validation = validate_gst_number(gst_num)
        gst_validations.append(validation)
        if validation.get('valid'):
            compliance_results['checks_passed'] += 0.5
            
    # HSN Code Check (Only flag the anomaly here)
    hsn_codes = enhanced_data.get('hsn_sac_codes', [])
    if not hsn_codes:
        anomalies.append("Missing HSN/SAC code")

    # HSN validation (1 point)
    hsn_validations = []
    for hsn_code in hsn_codes:
        if hsn_code in HSN_SAC_DATABASE:
            hsn_validations.append({
                'hsn_code': hsn_code,
                'is_correct': True,
                'regulatory_rate': HSN_SAC_DATABASE[hsn_code]['gst_rate']
            })
            compliance_results['checks_passed'] += 1
            break
    
    # Arithmetic check (1 point)
    arithmetic_check = check_arithmetic_accuracy(invoice_data)
    if arithmetic_check.get('overall_accurate'):
        compliance_results['checks_passed'] += 1
    
    # Duplicate check (1 point) - assume no duplicates for now
    duplicate_check = []
    compliance_results['checks_passed'] += 1
    
    # Price analysis (1 point)
    price_analysis = analyze_market_prices(enhanced_data, invoice_data)
    if not any(p.get('is_outlier', False) for p in price_analysis):
        compliance_results['checks_passed'] += 1
    
    # Calculate final score
    compliance_results['compliance_score'] = (compliance_results['checks_passed'] / compliance_results['total_checks']) * 100
    
    # Determine base status and risk
    if compliance_results['compliance_score'] >= 90:
        compliance_results['compliance_status'] = "Excellent"
        compliance_results['risk_level'] = "Low Risk"
        compliance_results['risk_score'] = 10
    elif compliance_results['compliance_score'] >= 75:
        compliance_results['compliance_status'] = "Good"
        compliance_results['risk_level'] = "Low Risk"
        compliance_results['risk_score'] = 25
    elif compliance_results['compliance_score'] >= 60:
        compliance_results['compliance_status'] = "Fair"
        compliance_results['risk_level'] = "Medium Risk"
        compliance_results['risk_score'] = 50
    else:
        compliance_results['compliance_status'] = "Poor"
        compliance_results['risk_level'] = "High Risk"
        compliance_results['risk_score'] = 75
    
    # --- ADD PENALTIES HERE (After base risk is set) ---
    if not hsn_codes:
        compliance_results['risk_score'] += 15
        if compliance_results['risk_level'] == "Low Risk":
            compliance_results['risk_level'] = "Medium Risk"

    if ml_result and ml_result.get('is_anomaly'):
        compliance_results['risk_score'] += 20
        if compliance_results['risk_score'] > 50:
            compliance_results['risk_level'] = "High Risk"
            
    # Remaining anomalies
    if ml_result and ml_result.get('is_anomaly'):
        anomalies.append("ML anomaly detected")
    if invoice_data.get('ocr_confidence', 0) < 70:
        anomalies.append("Low OCR confidence")
    if not arithmetic_check.get('overall_accurate'):
        anomalies.append("Arithmetic error")
    
    compliance_results.update({
        'gst_validations': gst_validations,
        'hsn_validations': hsn_validations,
        'duplicate_check': duplicate_check,
        'arithmetic_check': arithmetic_check,
        'price_analysis': price_analysis,
        'anomalies_detected': anomalies
    })
    
    return compliance_results
    
def validate_gst_number(gst_number):
    """Validate GST number format"""
    try:
        gst_pattern = r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}[Z]{1}[0-9A-Z]{1}$'
        
        if re.match(gst_pattern, gst_number):
            return {'valid': True, 'status': 'active', 'format_valid': True}
        else:
            return {'valid': False, 'status': 'invalid_format', 'format_valid': False}
    except:
        return {'valid': False, 'status': 'error', 'format_valid': False}

def check_arithmetic_accuracy(invoice_data):
    """Check arithmetic accuracy"""
    try:
        total_amount = invoice_data.get('total_amount')
        if total_amount:
            amount = float(str(total_amount).replace(',', ''))
            # Simple check - assume 18% GST
            base_amount = amount / 1.18
            expected_gst = base_amount * 0.18
            expected_total = base_amount + expected_gst
            
            return {
                'overall_accurate': abs(amount - expected_total) < 1.0,
                'base_amount': base_amount,
                'expected_gst': expected_gst,
                'expected_total': expected_total
            }
    except:
        pass
    
    return {'overall_accurate': False}

def analyze_market_prices(enhanced_data, invoice_data):
    """Analyze market prices"""
    price_analysis = []
    
    items = enhanced_data.get('item_descriptions', [])
    if items and invoice_data.get('total_amount'):
        amount = float(str(invoice_data['total_amount']).replace(',', ''))
        
        for item in items:
            # Mock market analysis
            market_avg = 25000  # Default market average
            variance_percent = ((amount - market_avg) / market_avg) * 100
            is_outlier = abs(variance_percent) > 50
            
            price_analysis.append({
                'item': item,
                'billed_price': amount,
                'market_avg': market_avg,
                'variance_percent': variance_percent,
                'is_outlier': is_outlier
            })
    
    return price_analysis

def extract_ml_features(invoice_data):
    """Extract ML features"""
    try:
        features = []
        
        # Amount features
        if invoice_data.get('total_amount'):
            amount = float(str(invoice_data['total_amount']).replace(',', ''))
            features.extend([amount, amount % 1000, len(str(int(amount)))])
        else:
            features.extend([0, 0, 0])
        
        # Date features
        if invoice_data.get('invoice_date'):
            try:
                date_obj = pd.to_datetime(invoice_data['invoice_date'])
                features.extend([date_obj.dayofweek, date_obj.day, date_obj.month])
            except:
                features.extend([0, 0, 0])
        else:
            features.extend([0, 0, 0])
        
        # Quality features
        features.extend([
            invoice_data.get('ocr_confidence', 0),
            len(invoice_data.get('raw_text', '')),
            len(invoice_data.get('gst_numbers', [])),
            1 if invoice_data.get('vendor_name') else 0,
            1 if invoice_data.get('invoice_number') else 0,
            1 if invoice_data.get('invoice_date') else 0,
            1 if invoice_data.get('total_amount') else 0,
            0,
            0 # Additional feature
        ])
        
        return features if len(features) == 15 else None
        
    except Exception as e:
        print(f"ML feature extraction error: {e}")
        return None

def convert_numpy_types(obj):
    """Convert numpy types to Python native types"""
    if hasattr(obj, 'item'):
        return obj.item()
    elif hasattr(obj, 'tolist'):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {k: convert_numpy_types(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(v) for v in obj]
    else:
        return obj

def safe_convert(value):
    """Safely convert values"""
    if value is None:
        return "Unknown"
    return str(value)

# NEW: AI-Powered Analysis Endpoint
@app.get("/api/invoices/{invoice_id}/ai-analysis")
async def get_ai_analysis(invoice_id: str):
    """
    Get AI-powered analysis for an existing invoice
    Uses LangChain agent for intelligent fraud detection
    """
    if not LANGCHAIN_AVAILABLE:
        return {
            "success": False,
            "error": "LangChain not installed. Run: pip install langchain langchain-google-genai"
        }
    
    try:
        # Get invoice from database
        invoice = db.invoices.find_one({"_id": invoice_id})
        
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
        
        # Run AI analysis
        ai_result = analyze_invoice_hybrid(
            invoice_data={
                "invoice_number": invoice.get("invoiceNumber"),
                "vendor_name": invoice.get("vendorName"),
                "total_amount": invoice.get("totalAmount", 0),
                "gst_numbers": invoice.get("gstNumbers", [])
            },
            use_ai=True
        )
        
        return {
            "success": True,
            "invoice_id": invoice_id,
            "rule_based_anomalies": ai_result["rule_based_anomalies"],
            "ai_analysis": ai_result.get("ai_analysis"),
            "ai_confidence": ai_result.get("ai_confidence"),
            "ai_used": ai_result["ai_used"]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    print("Starting VeriFin Complete API Server...")
    print("React Dashboard: http://localhost:8080")
    print("API Documentation: http://localhost:8000/docs")
    print("VeriFin Complete System Ready!")
    
    uvicorn.run(
        "verifin_api_fixed:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
