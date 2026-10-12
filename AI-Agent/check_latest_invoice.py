"""
Check latest invoice in MongoDB and verify GST
"""

from database import VeriFinDatabase
from gst_verifier import GSTVerifier

print("=" * 70)
print("📊 CHECKING LATEST INVOICE IN MONGODB")
print("=" * 70)
print()

# Connect to database
db = VeriFinDatabase()

# Get latest invoice
invoices = list(db.invoices.find().sort('_id', -1).limit(1))

if not invoices:
    print("❌ No invoices found in database!")
else:
    invoice = invoices[0]
    
    print("✅ LATEST INVOICE FOUND:")
    print("-" * 70)
    print(f"Invoice Number: {invoice.get('invoiceNumber', 'N/A')}")
    print(f"Vendor Name: {invoice.get('vendorName', 'N/A')}")
    print(f"Total Amount: ₹{invoice.get('totalAmount', 0):,.2f}")
    print(f"Invoice Date: {invoice.get('invoiceDate', 'N/A')}")
    print(f"GST Numbers: {invoice.get('gstNumbers', [])}")
    print(f"Upload Date: {invoice.get('uploadDate', 'N/A')}")
    print(f"Filename: {invoice.get('filename', 'N/A')}")
    print("-" * 70)
    print()
    
    # Check if data is properly stored
    print("✅ DATA STORED IN MONGODB: YES")
    print()

db.close()

# Now verify the specific GST number
print("=" * 70)
print("🔍 VERIFYING GST NUMBER: 24ABYFM2874M1ZD")
print("=" * 70)
print()

verifier = GSTVerifier()
result = verifier.verify_gst("24ABYFM2874M1ZD")

if result.get('success'):
    print("✅ GST VALIDATION SUCCESSFUL!")
    print("-" * 70)
    print(f"GST Number: {result.get('gstin', 'N/A')}")
    print(f"Legal Name: {result.get('legal_name', 'N/A')}")
    print(f"Trade Name: {result.get('trade_name', 'N/A')}")
    print(f"Status: {result.get('status', 'N/A')}")
    print(f"Active: {result.get('is_active', False)}")
    print(f"Registration Date: {result.get('registration_date', 'N/A')}")
    print(f"State: {result.get('state', 'N/A')}")
    print(f"Address: {result.get('address', 'N/A')}")
    print("-" * 70)
else:
    print("❌ GST VALIDATION FAILED!")
    print(f"Error: {result.get('error', 'Unknown error')}")

print()
print("=" * 70)
