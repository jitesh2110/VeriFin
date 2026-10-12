# 🤖 VeriFin - Backend

**AI Agent for Expense Anomaly & Compliance at Adani Finance**

VeriFin is an intelligent system that automates invoice processing, detects anomalies, validates compliance, and provides AI-powered insights for financial operations.

## 🚀 Features

### 🔍 **OCR & Data Extraction**
- **AI-powered OCR** using Tesseract for PDF/Image processing
- **80%+ accuracy** in extracting invoice data
- **Structured data extraction**: Invoice number, amount, date, GST numbers, HSN/SAC codes
- **Multi-format support**: PDF, JPEG, PNG, GIF

### 🚨 **Anomaly Detection**
- **Duplicate detection** using fuzzy matching algorithms
- **Price anomaly detection** with statistical analysis
- **GST compliance validation** against government portal
- **Arithmetic accuracy checking**
- **Suspicious pattern recognition**

### 🧠 **AI/ML Capabilities**
- **Risk scoring engine** (0-100 scale)
- **Pattern learning** from historical data
- **Vendor behavior profiling**
- **Continuous model improvement**

### 💬 **Natural Language Interface**
- **Chat-based queries**: "Show me top 5 anomalies this week"
- **Intelligent query parsing**
- **Contextual responses**

## 🏗️ Architecture

```
VeriFin Backend
├── 📄 OCR Service (Tesseract)
├── 🧠 AI Anomaly Engine
├── ✅ GST Validation Service
├── 💾 MongoDB Database
├── 🌐 REST API (Express)
└── 💬 NLP Chat Interface
```

## 📦 Installation

### Prerequisites
- ✅ Node.js 18+
- ✅ MongoDB Server
- ✅ Tesseract OCR

### Setup
```bash
# Clone and install dependencies
cd Backend
npm install

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Start MongoDB service
net start MongoDB

# Run VeriFin
npm run dev
```

## 🔧 Configuration

Edit `.env` file:
```env
# Database
MONGODB_URI=mongodb://localhost:27017/verifin

# OCR
TESSERACT_PATH=C:\Program Files\Tesseract-OCR\tesseract.exe

# Server
PORT=5000
```

## 📚 API Endpoints

### 📄 **Invoice Processing**
```http
POST /api/invoices/upload          # Upload & process invoice
GET  /api/invoices/:id             # Get invoice details
GET  /api/invoices/:id/status      # Check processing status
GET  /api/invoices                 # List invoices (with filters)
PUT  /api/invoices/:id/correct     # Apply user corrections
DELETE /api/invoices/:id           # Delete invoice
```

### 🚨 **Anomaly Management**
```http
GET /api/anomalies/dashboard       # Anomaly dashboard data
GET /api/anomalies                 # List anomalies (with filters)
GET /api/anomalies/types           # Anomaly types & counts
PUT /api/anomalies/:id/resolve     # Mark anomaly as resolved
GET /api/anomalies/vendors/risk    # Vendor risk analysis
```

### 💬 **Chat Interface**
```http
POST /api/chat/query               # Natural language query
GET  /api/chat/suggestions         # Get query suggestions
```

### 🔍 **Health Check**
```http
GET /api/health                    # System status
```

## 🤖 AI Engine Details

### **OCR Intelligence**
```javascript
// Smart text extraction with pattern recognition
const ocrResult = await ocrService.extractText(filePath, fileType);
// Returns: { text, accuracy }
```

### **Anomaly Detection**
```javascript
// Multi-layered anomaly detection
const anomalies = await anomalyDetector.detectAnomalies(invoice);
// Detects: duplicates, price outliers, GST issues, arithmetic errors
```

### **Risk Scoring**
```javascript
// AI-powered risk assessment
const riskScore = invoice.calculateRiskScore();
// Returns: 0-100 risk score based on multiple factors
```

### **Natural Language Processing**
```javascript
// Chat interface for queries
const response = await chatService.processQuery("Show me top 5 anomalies");
// Understands natural language and returns structured results
```

## 📊 Data Models

### **Invoice Schema**
```javascript
{
  invoiceNumber: String,
  invoiceAmount: Number,
  invoiceDate: Date,
  vendorGSTNumber: String,
  companyGSTNumber: String,
  items: [{
    description: String,
    hsnSacCode: String,
    quantity: Number,
    rate: Number,
    amount: Number,
    gstRate: Number
  }],
  ocrAccuracy: Number,
  riskScore: Number,
  anomalies: [{
    type: String,
    severity: String,
    description: String,
    confidence: Number
  }],
  validationResults: {
    vendorGSTValid: Boolean,
    companyGSTValid: Boolean,
    hsnRatesValid: Boolean,
    arithmeticValid: Boolean
  }
}
```

## 🚨 Anomaly Types

| Type | Description | Severity |
|------|-------------|----------|
| `duplicate` | Potential duplicate invoice | Critical/High |
| `price_outlier` | Price deviation from market | High/Medium |
| `gst_mismatch` | Invalid GST rates | Medium |
| `arithmetic_error` | Calculation errors | High/Medium |
| `suspicious_pattern` | Unusual patterns | Low/Medium |

## 💬 Chat Examples

```
User: "Show me top 5 anomalies this week"
VeriFin: Here are the top 5 anomalies:
1. INV-001 - Potential duplicate (Confidence: 95.2%)
2. INV-002 - Price deviation of 45% (Confidence: 87.1%)
...

User: "Which vendors have highest risk scores?"
VeriFin: Here are the vendors with highest risk:
1. Vendor ABC - Risk Score: 85.3, Invoices: 12
2. Vendor XYZ - Risk Score: 78.9, Invoices: 8
...

User: "How many high-risk invoices today?"
VeriFin: I found 7 high-risk invoices today.
```

## 🔄 Processing Flow

```
1. 📤 Invoice Upload
   ↓
2. 🔍 OCR Text Extraction
   ↓
3. 📊 Structured Data Extraction
   ↓
4. ✅ GST Validation
   ↓
5. 🚨 Anomaly Detection
   ↓
6. 📈 Risk Score Calculation
   ↓
7. 💾 Database Storage
   ↓
8. 📱 Dashboard Update
```

## 🛡️ Security Features

- **File type validation**
- **Size limits (10MB)**
- **Input sanitization**
- **Error handling**
- **Rate limiting**

## 📈 Performance

- **OCR Processing**: ~2-5 seconds per invoice
- **Anomaly Detection**: ~1-2 seconds per invoice
- **Database Queries**: Optimized with indexes
- **Concurrent Processing**: Async/await patterns

## 🧪 Testing

```bash
# Test OCR service
curl -X POST http://localhost:5000/api/invoices/upload \
  -F "invoice=@sample-invoice.pdf"

# Test chat interface
curl -X POST http://localhost:5000/api/chat/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Show me high risk invoices"}'

# Check system health
curl http://localhost:5000/api/health
```

## 🔧 Troubleshooting

### **Common Issues**

1. **Tesseract not found**
   ```bash
   # Check Tesseract installation
   tesseract --version
   # Update TESSERACT_PATH in .env
   ```

2. **MongoDB connection failed**
   ```bash
   # Start MongoDB service
   net start MongoDB
   # Check connection string in .env
   ```

3. **OCR accuracy low**
   - Ensure high-quality images
   - Check Tesseract language packs
   - Verify file format support

## 📝 Logs

```bash
# View logs
tail -f logs/verifin.log

# Debug mode
NODE_ENV=development npm run dev
```

## 🚀 Deployment

```bash
# Production build
npm start

# PM2 deployment
pm2 start server.js --name "verifin"
```

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Commit changes
4. Push to branch
5. Create Pull Request

## 📄 License

MIT License - see LICENSE file for details.

## 🆘 Support

For issues and support:
- 📧 Email: support@verifin.com
- 📚 Documentation: [docs.verifin.com]
- 🐛 Issues: [GitHub Issues]

---

**VeriFin** - Revolutionizing Financial Intelligence with AI 🚀
