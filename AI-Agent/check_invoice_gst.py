import os
from pymongo import MongoClient

# Connect to MongoDB
client = MongoClient('mongodb://localhost:27017/')
db = client[os.getenv('MONGODB_DATABASE', 'verifin')]

# Get one invoice
invoice = db.invoices.find_one()

if invoice:
    print("📋 Sample Invoice Fields:")
    print("=" * 60)
    print(f"Invoice Number: {invoice.get('invoiceNumber')}")
    print(f"GST Number: {invoice.get('gstNumber')}")
    print(f"GST Verification: {invoice.get('gst_verification')}")
    print(f"GST Valid: {invoice.get('gst_valid')}")
    print(f"GST Status: {invoice.get('gst_status')}")
    print("\n🔍 All Invoice Keys:")
    for key in invoice.keys():
        print(f"  - {key}: {type(invoice[key]).__name__}")
else:
    print("❌ No invoices found!")

client.close()
