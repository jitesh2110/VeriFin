"""
MongoDB Database Module for VeriFin
Handles invoice storage, vendor tracking, and anomaly detection
"""

import os
import sys
import re
from pymongo import MongoClient, ASCENDING, DESCENDING
from datetime import datetime
from typing import Dict, List, Optional, Any
import json

# Ensure UTF-8 output on Windows terminal
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

class VeriFinDatabase:
    def __init__(self, connection_string="mongodb://localhost:27017/"):
        """Initialize MongoDB connection with multi-tenant support"""
        self.client = MongoClient(connection_string)
        self.default_db_name = os.getenv('MONGODB_DATABASE', 'verifin')
        self.db = self.client[self.default_db_name]
        
        # Default collections for backwards compatibility
        self.invoices = self.db['invoices']
        self.vendors = self.db['vendors']
        self.anomalies = self.db['anomalies']
        
        self._initialized_tenants = set()
        self._create_indexes_for_db(self.db)
        self._initialized_tenants.add(self.default_db_name)
        
        print("✅ MongoDB connected successfully!")
        print(f"   Default Database: {self.default_db_name}")
        print(f"   Multi-Tenant Abstraction: Active (Dynamic Database-Per-Tenant)")

    def get_tenant_db_name(self, company_id: Optional[str] = None) -> str:
        """Returns the isolated database name for a given tenant company"""
        if not company_id or company_id in ["default", "comp_default", "None"]:
            return self.default_db_name
        clean_id = re.sub(r'[^a-zA-Z0-9_-]', '_', str(company_id))
        return f"verifin_tenant_{clean_id}"

    def get_tenant_db(self, company_id: Optional[str] = None):
        """Get or initialize isolated database for tenant company"""
        db_name = self.get_tenant_db_name(company_id)
        tenant_db = self.client[db_name]
        if db_name not in self._initialized_tenants:
            self._create_indexes_for_db(tenant_db)
            self._initialized_tenants.add(db_name)
        return tenant_db

    def _create_indexes_for_db(self, target_db):
        """Create indexes for optimized queries on target database"""
        try:
            target_db['invoices'].create_index([("invoiceNumber", ASCENDING)], unique=False)
            target_db['invoices'].create_index([("gstNumber", ASCENDING)])
            target_db['invoices'].create_index([("vendorName", ASCENDING)])
            target_db['invoices'].create_index([("uploadDate", DESCENDING)])
            target_db['invoices'].create_index([("projectId", ASCENDING)])
            
            target_db['vendors'].create_index([("gstNumber", ASCENDING)], unique=True)
            target_db['vendors'].create_index([("vendorName", ASCENDING)])
            
            target_db['anomalies'].create_index([("invoiceId", ASCENDING)])
            target_db['anomalies'].create_index([("anomalyType", ASCENDING)])
            target_db['anomalies'].create_index([("severity", ASCENDING)])
            target_db['anomalies'].create_index([("projectId", ASCENDING)])
        except Exception as e:
            print(f"⚠️ Index creation warning on {target_db.name}: {e}")

    def _create_indexes(self):
        """Create indexes on default database"""
        self._create_indexes_for_db(self.db)
    
    def store_invoice(self, invoice_data: Dict[str, Any], company_id: str = "comp_default", project_id: str = "proj_default") -> str:
        """
        Store invoice in tenant database
        Returns: invoice_id
        """
        tenant_db = self.get_tenant_db(company_id)
        
        invoice_doc = {
            'companyId': company_id,
            'projectId': project_id,
            'filename': invoice_data.get('filename'),
            'uploadDate': datetime.now(),
            'invoiceNumber': invoice_data.get('invoice_number'),
            'vendorName': invoice_data.get('vendor_name'),
            'gstNumber': invoice_data.get('gst_numbers', [])[0] if invoice_data.get('gst_numbers') else None,
            'allGstNumbers': invoice_data.get('gst_numbers', []),
            'totalAmount': float(invoice_data.get('total_amount', 0)),
            'invoiceDate': invoice_data.get('invoice_date'),
            'gstRate': invoice_data.get('gst_rate', 'Unknown'),
            'hsnNumber': invoice_data.get('hsn_number', 'Unknown'),
            'hsnCodes': invoice_data.get('hsn_sac_codes', []),
            'itemDescriptions': invoice_data.get('item_descriptions', []),
            'quantities': invoice_data.get('quantities', []),
            'lineItems': invoice_data.get('line_items', []),
            'ocrConfidence': float(invoice_data.get('ocr_confidence', 0)),
            'complianceResults': invoice_data.get('compliance_results', {}),
            'mlPrediction': invoice_data.get('ml_prediction', {}),
            'imageUrl': invoice_data.get('image_url'),
            'thumbnailUrl': invoice_data.get('thumbnail_url'),
            'storageInfo': invoice_data.get('storage_info', {}),
            'isManualEntry': invoice_data.get('is_manual_entry', False),
            'processingStatus': invoice_data.get('processing_status', 'completed'),
            'rawText': invoice_data.get('raw_text', '')[:1000]  # Store first 1000 chars
        }
        
        result = tenant_db['invoices'].insert_one(invoice_doc)
        invoice_id = str(result.inserted_id)
        
        # Update vendor statistics in tenant database
        self._update_vendor_stats(invoice_doc, tenant_db=tenant_db)
        
        print(f"✅ Invoice stored in [{tenant_db.name}]: {invoice_doc['invoiceNumber']} (ID: {invoice_id})")
        return invoice_id
    
    def _update_vendor_stats(self, invoice_doc: Dict, tenant_db=None):
        """Update or create vendor statistics in tenant database"""
        if tenant_db is None:
            tenant_db = self.db
            
        gst_number = invoice_doc.get('gstNumber')
        vendor_name = invoice_doc.get('vendorName')
        
        if not gst_number or gst_number == 'Unknown':
            return
        
        vendor = tenant_db['vendors'].find_one({'gstNumber': gst_number})
        
        if vendor:
            # Update existing vendor
            tenant_db['vendors'].update_one(
                {'gstNumber': gst_number},
                {
                    '$inc': {
                        'totalInvoices': 1,
                        'totalAmount': invoice_doc.get('totalAmount', 0)
                    },
                    '$set': {
                        'lastInvoiceDate': datetime.now(),
                        'vendorName': vendor_name  # Update in case name changed
                    }
                }
            )
        else:
            # Create new vendor
            tenant_db['vendors'].insert_one({
                'gstNumber': gst_number,
                'vendorName': vendor_name,
                'totalInvoices': 1,
                'totalAmount': invoice_doc.get('totalAmount', 0),
                'firstInvoiceDate': datetime.now(),
                'lastInvoiceDate': datetime.now()
            })
    
    def detect_anomalies(self, invoice_data: Dict[str, Any], invoice_id: str, company_id: str = "comp_default", project_id: Optional[str] = None) -> List[Dict]:
        """
        Detect anomalies by comparing with historical data within tenant database
        Returns: List of detected anomalies
        """
        from bson import ObjectId
        tenant_db = self.get_tenant_db(company_id)
        anomalies = []
        
        # Convert invoice_id to ObjectId for comparison
        try:
            obj_id = ObjectId(invoice_id)
        except:
            obj_id = invoice_id
        
        # 1. Check for duplicate invoice number in tenant db
        duplicate = tenant_db['invoices'].find_one({
            'invoiceNumber': invoice_data.get('invoice_number'),
            '_id': {'$ne': obj_id}
        })
        if duplicate:
            anomalies.append({
                'type': 'DUPLICATE_INVOICE',
                'severity': 'HIGH',
                'description': f"Duplicate invoice number: {invoice_data.get('invoice_number')}",
                'relatedInvoiceId': str(duplicate['_id'])
            })
        
        # 2. Check for missing GST number
        gst_numbers = invoice_data.get('gst_numbers', [])
        gst_missing = invoice_data.get('gst_missing', False)
        
        if not gst_numbers or len(gst_numbers) == 0 or gst_missing:
            anomalies.append({
                'type': 'MISSING_GST',
                'severity': 'HIGH',
                'description': f"No GST number found in invoice - Vendor: {invoice_data.get('vendor_name', 'Unknown')}",
            })
        
        # 3. Check for invalid GST number
        gst_number = gst_numbers[0] if gst_numbers else None
        if gst_number:
            gst_verification = invoice_data.get('gst_verification', [])
            if gst_verification and len(gst_verification) > 0:
                verification_result = gst_verification[0]
                if not verification_result.get('success') or not verification_result.get('is_active'):
                    anomalies.append({
                        'type': 'INVALID_GST',
                        'severity': 'HIGH',
                        'description': f"Invalid GST number: {gst_number} - Verification failed",
                    })
        
        # 4. Check for GST number with different vendor name in tenant db
        if gst_number:
            different_vendor = tenant_db['invoices'].find_one({
                'gstNumber': gst_number,
                'vendorName': {'$ne': invoice_data.get('vendor_name')},
                '_id': {'$ne': obj_id}
            })
            if different_vendor:
                anomalies.append({
                    'type': 'GST_VENDOR_MISMATCH',
                    'severity': 'HIGH',
                    'description': f"GST {gst_number} used by different vendor: {different_vendor.get('vendorName')} vs {invoice_data.get('vendor_name')}",
                    'relatedInvoiceId': str(different_vendor['_id'])
                })
        
        # 5. Check for unusual amount from same vendor
        vendor_name = invoice_data.get('vendor_name')
        if vendor_name and vendor_name != 'Unknown':
            stats = list(self.vendors_stats(vendor_name, tenant_db=tenant_db))
            if stats:
                avg_amount = stats[0].get('avgAmount', 0)
                current_amount = float(invoice_data.get('total_amount', 0))
                
                if avg_amount > 0 and current_amount > (avg_amount * 3):
                    anomalies.append({
                        'type': 'UNUSUAL_AMOUNT',
                        'severity': 'MEDIUM',
                        'description': f"Amount ₹{current_amount} is 3x higher than vendor average ₹{avg_amount:.2f}"
                    })

        # Check for missing HSN / SAC codes
        hsn_codes = invoice_data.get('hsn_sac_codes', [])
        line_items = invoice_data.get('line_items', [])
        has_items_without_hsn = any(not item.get('hsn_code') for item in line_items) if line_items else False

        if (not hsn_codes or len(hsn_codes) == 0) or has_items_without_hsn:
            anomalies.append({
                'type': 'MISSING_HSN_SAC',
                'severity': 'MEDIUM',
                'description': f"Missing HSN/SAC code in invoice: {invoice_data.get('invoice_number')}"
            })
        
        # Check for invalid HSN/SAC codes
        hsn_sac_verification = invoice_data.get('hsn_sac_verification', [])
        if hsn_sac_verification:
            invalid_codes = [v for v in hsn_sac_verification if not v.get('is_valid')]
            if invalid_codes:
                for invalid in invalid_codes:
                    anomalies.append({
                        'type': 'INVALID_HSN_SAC',
                        'severity': 'HIGH',
                        'description': f"Invalid HSN/SAC code: {invalid.get('code')} - {invalid.get('error', 'Not found in GST database')}"
                    })
        
        # Check for GST rate mismatches in line items
        line_items_verification = invoice_data.get('hsn_sac_line_items_verification')
        if line_items_verification and line_items_verification.get('rate_mismatches'):
            for mismatch in line_items_verification['rate_mismatches']:
                anomalies.append({
                    'type': 'HSN_GST_RATE_MISMATCH',
                    'severity': 'HIGH',
                    'description': f"GST rate mismatch for {mismatch['item']}: HSN {mismatch['hsn_code']} should have {mismatch['actual_rate']}% but invoice shows {mismatch['extracted_rate']}%"
                })
        
        # Check for same HSN code with very different price
        if hsn_codes:
            for hsn in hsn_codes[:3]:
                similar_invoices = list(tenant_db['invoices'].find({
                    'hsnCodes': hsn,
                    '_id': {'$ne': obj_id}
                }).limit(10))
                
                if len(similar_invoices) >= 3:
                    amounts = [inv['totalAmount'] for inv in similar_invoices if inv.get('totalAmount', 0) > 0]
                    if amounts:
                        avg_hsn_amount = sum(amounts) / len(amounts)
                        current_amount = float(invoice_data.get('total_amount', 0))
                        
                        if avg_hsn_amount > 0 and abs(current_amount - avg_hsn_amount) > (avg_hsn_amount * 0.5):
                            anomalies.append({
                                'type': 'HSN_PRICE_DEVIATION',
                                'severity': 'MEDIUM',
                                'description': f"HSN {hsn}: Amount ₹{current_amount} deviates significantly from historical average ₹{avg_hsn_amount:.2f}"
                            })
                            break
        
        # Store anomalies in tenant database
        for anomaly in anomalies:
            tenant_db['anomalies'].insert_one({
                'companyId': company_id,
                'projectId': project_id or 'proj_default',
                'invoiceId': invoice_id,
                'invoiceNumber': invoice_data.get('invoice_number'),
                'anomalyType': anomaly['type'],
                'severity': anomaly['severity'],
                'description': anomaly['description'],
                'detectedDate': datetime.now(),
                'relatedInvoiceId': anomaly.get('relatedInvoiceId')
            })
        
        return anomalies
    
    def vendors_stats(self, vendor_name: str, tenant_db=None) -> List[Dict]:
        """Get statistics for a vendor in tenant database"""
        if tenant_db is None:
            tenant_db = self.db
        pipeline = [
            {'$match': {'vendorName': vendor_name}},
            {'$group': {
                '_id': None,
                'avgAmount': {'$avg': '$totalAmount'},
                'maxAmount': {'$max': '$totalAmount'},
                'minAmount': {'$min': '$totalAmount'},
                'totalInvoices': {'$sum': 1}
            }}
        ]
        return list(tenant_db['invoices'].aggregate(pipeline))
    
    def get_invoice_history(self, limit: int = 50, company_id: str = "comp_default", project_id: Optional[str] = None) -> List[Dict]:
        """Get recent invoice history with anomalies from tenant database"""
        tenant_db = self.get_tenant_db(company_id)
        query = {}
        if project_id and project_id not in ["all", "None", ""]:
            query['projectId'] = project_id

        invoices = list(tenant_db['invoices'].find(query).sort('uploadDate', DESCENDING).limit(limit))
        
        # Convert ObjectId to string and attach anomalies
        for inv in invoices:
            invoice_id = inv['_id']
            inv['_id'] = str(inv['_id'])
            inv['uploadDate'] = inv['uploadDate'].isoformat() if inv.get('uploadDate') else None
            
            # Fetch anomalies for this invoice from tenant db
            anomalies = list(tenant_db['anomalies'].find({'invoiceId': invoice_id}))
            for anomaly in anomalies:
                anomaly['_id'] = str(anomaly['_id'])
                if anomaly.get('detectedDate'):
                    anomaly['detectedDate'] = anomaly['detectedDate'].isoformat()
            inv['anomalies'] = anomalies
        
        return invoices
    
    def get_vendor_list(self, company_id: str = "comp_default") -> List[Dict]:
        """Get list of all vendors in tenant database"""
        tenant_db = self.get_tenant_db(company_id)
        vendors = list(tenant_db['vendors'].find().sort('totalAmount', DESCENDING))
        
        for vendor in vendors:
            vendor['_id'] = str(vendor['_id'])
            vendor['firstInvoiceDate'] = vendor['firstInvoiceDate'].isoformat() if vendor.get('firstInvoiceDate') else None
            vendor['lastInvoiceDate'] = vendor['lastInvoiceDate'].isoformat() if vendor.get('lastInvoiceDate') else None
        
        return vendors
    
    def get_anomalies(self, severity: Optional[str] = None, limit: int = 50, company_id: str = "comp_default", project_id: Optional[str] = None) -> List[Dict]:
        """Get detected anomalies from tenant database with vendor information"""
        tenant_db = self.get_tenant_db(company_id)
        query = {}
        if severity:
            query['severity'] = severity
        if project_id and project_id not in ["all", "None", ""]:
            query['projectId'] = project_id
        
        anomalies = list(tenant_db['anomalies'].find(query).sort('detectedDate', DESCENDING).limit(limit))
        
        for anomaly in anomalies:
            anomaly['_id'] = str(anomaly['_id'])
            anomaly['detectedDate'] = anomaly['detectedDate'].isoformat() if anomaly.get('detectedDate') else None
            
            # Fetch vendor name from tenant invoices
            if anomaly.get('invoiceId'):
                invoice = tenant_db['invoices'].find_one({'_id': anomaly['invoiceId']})
                if invoice:
                    anomaly['vendor_name'] = invoice.get('vendorName', 'Unknown')
                    anomaly['invoice_number'] = invoice.get('invoiceNumber', anomaly.get('invoiceNumber', 'N/A'))
                else:
                    anomaly['vendor_name'] = 'Unknown'
            else:
                anomaly['vendor_name'] = 'Unknown'
        
        return anomalies
    
    def get_dashboard_stats(self, company_id: str = "comp_default", project_id: Optional[str] = None) -> Dict:
        """Get statistics for dashboard from tenant database"""
        tenant_db = self.get_tenant_db(company_id)
        query = {}
        if project_id and project_id not in ["all", "None", ""]:
            query['projectId'] = project_id

        total_invoices = tenant_db['invoices'].count_documents(query)
        total_vendors = tenant_db['vendors'].count_documents({})
        total_anomalies = tenant_db['anomalies'].count_documents(query)
        high_severity_anomalies = tenant_db['anomalies'].count_documents({**query, 'severity': 'HIGH'})
        
        # Total amount processed
        pipeline = []
        if query:
            pipeline.append({'$match': query})
        pipeline.append({
            '$group': {
                '_id': None,
                'totalAmount': {'$sum': '$totalAmount'}
            }
        })
        amount_result = list(tenant_db['invoices'].aggregate(pipeline))
        total_amount = amount_result[0]['totalAmount'] if amount_result else 0
        
        return {
            'totalInvoices': total_invoices,
            'totalVendors': total_vendors,
            'totalAnomalies': total_anomalies,
            'highSeverityAnomalies': high_severity_anomalies,
            'totalAmountProcessed': total_amount,
            'companyId': company_id,
            'database': tenant_db.name
        }
    
    def get_anomaly_trends(self, days: int = 30, company_id: str = "comp_default", project_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get anomaly trends for the last N days from tenant database
        Returns daily counts of each anomaly type
        """
        from datetime import timedelta
        tenant_db = self.get_tenant_db(company_id)
        
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        match_query = {
            'detectedDate': {'$gte': start_date, '$lte': end_date}
        }
        if project_id and project_id not in ["all", "None", ""]:
            match_query['projectId'] = project_id

        pipeline = [
            {'$match': match_query},
            {
                '$group': {
                    '_id': {
                        'date': {'$dateToString': {'format': '%Y-%m-%d', 'date': '$detectedDate'}},
                        'type': '$anomalyType'
                    },
                    'count': {'$sum': 1}
                }
            },
            {'$sort': {'_id.date': 1}}
        ]
        
        results = list(tenant_db['anomalies'].aggregate(pipeline))
        
        # Organize data by date
        trends_by_date = {}
        for result in results:
            date = result['_id']['date']
            anomaly_type = result['_id']['type']
            count = result['count']
            
            if date not in trends_by_date:
                trends_by_date[date] = {
                    'date': date,
                    'duplicates': 0,
                    'invalidGst': 0,
                    'missingGst': 0,
                    'hsnAnomalies': 0,
                    'total': 0
                }
            
            # Map anomaly types to keys
            if anomaly_type == 'DUPLICATE_INVOICE':
                trends_by_date[date]['duplicates'] += count
            elif anomaly_type in ['INVALID_GST', 'GST_VENDOR_MISMATCH']:
                trends_by_date[date]['invalidGst'] += count
            elif anomaly_type == 'MISSING_GST':
                trends_by_date[date]['missingGst'] += count
            elif anomaly_type in ['INVALID_HSN_SAC', 'HSN_GST_RATE_MISMATCH', 'HSN_PRICE_DEVIATION', 'UNUSUAL_AMOUNT']:
                trends_by_date[date]['hsnAnomalies'] += count
            
            trends_by_date[date]['total'] += count
        
        # Fill in missing dates with zeros
        all_trends = []
        current_date = start_date
        while current_date <= end_date:
            date_str = current_date.strftime('%Y-%m-%d')
            if date_str in trends_by_date:
                all_trends.append(trends_by_date[date_str])
            else:
                all_trends.append({
                    'date': date_str,
                    'duplicates': 0,
                    'invalidGst': 0,
                    'missingGst': 0,
                    'hsnAnomalies': 0,
                    'total': 0
                })
            current_date += timedelta(days=1)
        
        return all_trends
    
    def close(self):
        """Close database connection"""
        self.client.close()
        print("MongoDB connection closed")


# Backwards compatibility alias
FintelDatabase = VeriFinDatabase


# Test connection
if __name__ == "__main__":
    db = VeriFinDatabase()
    print("\n📊 Database Stats:")
    stats = db.get_dashboard_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    db.close()
