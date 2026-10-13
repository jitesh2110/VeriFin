import { useState, useEffect, useRef } from "react";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Upload as UploadIcon, FileText, CheckCircle, AlertCircle, Clock, Calendar, Edit3, Image as ImageIcon, Building2 } from "lucide-react";
import { Progress } from "@/components/ui/progress";
import { toast } from "sonner";
import { ManualInvoiceModal } from "@/components/invoices/ManualInvoiceModal";
import { fetchWithTenant, AI_AGENT_BASE } from "@/lib/apiClient";
import { useAuth } from "@/contexts/AuthContext";

interface UploadedFile {
  id: string;
  name: string;
  uploadTime: string;
  uploadedAt?: string;
  status: "processing" | "completed" | "error" | "needs_manual_review";
  accuracy: number;
  progress: number;
  draftId?: string;
  imageUrl?: string;
  thumbnailUrl?: string;
  extractedData?: {
    // Basic extraction
    invoiceNumber: string;
    vendorName: string;
    invoiceAmount: number;
    invoiceDate: string;
    gstNumbers: string[];
    gstRate?: string;
    hsnNumber?: string;
    ocrConfidence: number;
    imageUrl?: string;
    thumbnailUrl?: string;
    draftId?: string;
    isManualEntry?: boolean;
    
    // Enhanced extraction
    hsnSacCodes?: string[];
    itemDescriptions?: string[];
    quantities?: number[];
    
    // Compliance scoring
    complianceScore?: number;
    complianceStatus?: string;
    checksPassedCount?: number;
    totalChecksCount?: number;
    riskScore?: number;
    riskLevel?: string;
    
    // Validation results
    gstValidations?: Array<{valid: boolean, status: string}>;
    hsnValidations?: Array<{is_correct: boolean, hsn_code: string}>;
    duplicateCheck?: Array<any>;
    arithmeticCheck?: {overall_accurate: boolean};
    priceAnalysis?: Array<{
      item: string;
      billed_price: number;
      variance_percent: number;
      is_outlier: boolean;
    }>;
    
    // GST Verification (Government API)
    gstVerification?: Array<{
      success: boolean;
      is_valid: boolean;
      is_active: boolean;
      gst_number: string;
      legal_name?: string;
      status?: string;
      error?: string;
    }>;
    
    // ML results
    mlPrediction?: {
      is_anomaly: boolean;
      confidence: number;
    };
    
    // Anomalies summary
    anomaliesDetected?: string[];
  };
  error?: string;
}

const Upload = () => {
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isLoadingHistory, setIsLoadingHistory] = useState(true);
  
  // Mid-layer manual entry modal state
  const [isManualModalOpen, setIsManualModalOpen] = useState(false);
  const [manualModalData, setManualModalData] = useState<any>(undefined);
  
  const { companyName, companyId, activeProjectId } = useAuth();

  // Load past invoices from MongoDB on component mount or tenant change
  useEffect(() => {
    loadInvoiceHistory();
  }, [companyId, activeProjectId]);

  const loadInvoiceHistory = async () => {
    try {
      setIsLoadingHistory(true);
      const response = await fetchWithTenant(`${AI_AGENT_BASE}/api/invoices/history?limit=25`);
      const data = await response.json();
      
      if (data.success && data.invoices) {
        const historicalFiles: UploadedFile[] = data.invoices.map((inv: any) => ({
          id: inv._id || inv.id,
          name: inv.filename || inv.fileName || 'invoice.pdf',
          uploadTime: inv.uploadDate ? new Date(inv.uploadDate).toLocaleString('en-IN') : 'Unknown',
          uploadedAt: inv.uploadDate,
          status: inv.processingStatus === "needs_manual_review" ? "needs_manual_review" : "completed",
          accuracy: inv.ocrConfidence || inv.ocr_confidence || 0,
          progress: 100,
          draftId: inv._id || inv.id,
          imageUrl: inv.imageUrl || inv.image_url,
          thumbnailUrl: inv.thumbnailUrl || inv.thumbnail_url,
          extractedData: {
            invoiceNumber: inv.invoiceNumber || inv.invoice_number || 'Unknown',
            vendorName: inv.vendorName || inv.vendor_name || 'Unknown',
            invoiceAmount: inv.totalAmount || inv.total_amount || 0,
            invoiceDate: inv.invoiceDate || inv.invoice_date || 'Unknown',
            gstNumbers: inv.allGstNumbers || inv.all_gst_numbers || inv.gst_numbers || [],
            gstRate: inv.gstRate || inv.gst_rate || 'Unknown',
            hsnNumber: inv.hsnNumber || inv.hsn_number || 'Unknown',
            ocrConfidence: inv.ocrConfidence || inv.ocr_confidence || 0,
            imageUrl: inv.imageUrl || inv.image_url,
            thumbnailUrl: inv.thumbnailUrl || inv.thumbnail_url,
            draftId: inv._id || inv.id,
            isManualEntry: inv.isManualEntry || inv.is_manual_entry || false,
            // Load validation results from compliance data
            gstValidations: inv.complianceResults?.gst_validations || inv.compliance_results?.gst_validations || [],
            hsnValidations: inv.complianceResults?.hsn_validations || inv.compliance_results?.hsn_validations || [],
            duplicateCheck: inv.complianceResults?.duplicate_check || inv.compliance_results?.duplicate_check || [],
            arithmeticCheck: inv.complianceResults?.arithmetic_check || inv.compliance_results?.arithmetic_check || {overall_accurate: false},
            complianceScore: inv.complianceResults?.compliance_score || inv.compliance_results?.compliance_score || 0,
            complianceStatus: inv.complianceResults?.compliance_status || inv.compliance_results?.compliance_status || 'Unknown',
            riskScore: inv.complianceResults?.risk_score || inv.compliance_results?.risk_score || 0,
            riskLevel: inv.complianceResults?.risk_level || inv.compliance_results?.risk_level || 'Unknown',
            gstVerification: inv.gstVerification || inv.gst_verification || [],
            anomaliesDetected: inv.anomalies?.map((a: any) => a.description || a.anomalyType || a.anomaly_type) || [],
          }
        }));
        setFiles(historicalFiles);
      }
    } catch (error) {
      console.error('❌ Failed to load invoice history:', error);
    } finally {
      setIsLoadingHistory(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const droppedFiles = Array.from(e.dataTransfer.files);
    handleFiles(droppedFiles);
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      handleFiles(Array.from(e.target.files));
      // Reset file input to allow uploading the same file again
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleFiles = async (uploadedFiles: File[]) => {
    const newFiles: UploadedFile[] = uploadedFiles.map((file, index) => ({
      id: `${Date.now()}-${index}`,
      name: file.name,
      uploadTime: "Just now",
      uploadedAt: new Date().toISOString(),
      status: "processing",
      accuracy: 0,
      progress: 0,
    }));

    setFiles([...newFiles, ...files]);
    toast.success(`${uploadedFiles.length} file(s) uploaded successfully`);

    // REAL API CALL instead of simulation
    for (let i = 0; i < uploadedFiles.length; i++) {
      const file = uploadedFiles[i];
      const fileId = newFiles[i].id;
      
      try {
        // Update progress to show processing
        setFiles(prev => prev.map(f => 
          f.id === fileId ? { ...f, progress: 50 } : f
        ));

        // Call REAL FINTEL AI API with tenant context
        const formData = new FormData();
        formData.append('file', file);

        const response = await fetchWithTenant(`${AI_AGENT_BASE}/api/invoices/upload`, {
          method: 'POST',
          body: formData,
        });

        console.log('Response status:', response.status);

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const result = await response.json();
        console.log('API Response:', result);

        if (result.success) {
          // Update with COMPLETE extracted data including all compliance features
          setFiles(prev => prev.map(f => 
            f.id === fileId ? {
              ...f,
              progress: 100,
              status: "completed",
              draftId: result.data.invoiceId,
              imageUrl: result.imageUrl || result.data.imageUrl,
              thumbnailUrl: result.thumbnailUrl || result.data.thumbnailUrl,
              accuracy: result.data.ocrConfidence || 0, // REAL accuracy from OCR
              extractedData: {
                // Basic extraction
                invoiceNumber: result.data.invoiceNumber || 'Unknown',
                vendorName: result.data.vendorName || 'Unknown',
                invoiceAmount: result.data.invoiceAmount || 0,
                invoiceDate: result.data.invoiceDate || 'Unknown',
                gstNumbers: result.data.gstNumbers || [],
                gstRate: result.data.gstRate || result.data.gst_rate || 'Unknown',
                hsnNumber: result.data.hsnNumber || result.data.hsn_number || 'Unknown',
                ocrConfidence: result.data.ocrConfidence || 0,
                imageUrl: result.imageUrl || result.data.imageUrl,
                thumbnailUrl: result.thumbnailUrl || result.data.thumbnailUrl,
                draftId: result.data.invoiceId,
                isManualEntry: result.data.isManualEntry || false,
                
                // Enhanced extraction
                hsnSacCodes: result.data.hsnSacCodes || [],
                itemDescriptions: result.data.itemDescriptions || [],
                quantities: result.data.quantities || [],
                
                // Compliance scoring
                complianceScore: result.data.complianceScore || 0,
                complianceStatus: result.data.complianceStatus || 'Unknown',
                checksPassedCount: result.data.checksPassedCount || 0,
                totalChecksCount: result.data.totalChecksCount || 12,
                riskScore: result.data.riskScore || 0,
                riskLevel: result.data.riskLevel || 'Unknown',
                
                // Validation results
                gstValidations: result.data.gstValidations || [],
                hsnValidations: result.data.hsnValidations || [],
                duplicateCheck: result.data.duplicateCheck || [],
                arithmeticCheck: result.data.arithmeticCheck || {overall_accurate: false},
                priceAnalysis: result.data.priceAnalysis || [],
                
                // ML results
                mlPrediction: result.data.mlPrediction || {is_anomaly: false, confidence: 0},
                
                // Anomalies summary
                anomaliesDetected: result.data.anomaliesDetected || []
              }
            } : f
          ));
          
          toast.success(`${file.name} processed successfully!`);
        } else if (result.needs_manual_review) {
          // Mid-Layer Fallback: AI OCR broke down or had low confidence (<65%)
          setFiles(prev => prev.map(f => 
            f.id === fileId ? {
              ...f,
              progress: 100,
              status: "needs_manual_review",
              draftId: result.draftId,
              imageUrl: result.imageUrl,
              thumbnailUrl: result.thumbnailUrl,
              accuracy: result.partialData?.ocrConfidence || 0,
              extractedData: {
                invoiceNumber: result.partialData?.invoiceNumber || 'Unknown',
                vendorName: result.partialData?.vendorName || 'Unknown',
                invoiceAmount: result.partialData?.invoiceAmount || 0,
                invoiceDate: result.partialData?.invoiceDate || 'Unknown',
                gstNumbers: result.partialData?.gstNumbers || [],
                ocrConfidence: result.partialData?.ocrConfidence || 0,
                imageUrl: result.imageUrl,
                thumbnailUrl: result.thumbnailUrl,
                draftId: result.draftId,
                isManualEntry: false,
              }
            } : f
          ));

          toast.warning(`OCR confidence was low (<65%). Draft saved. Please review manually.`, {
            duration: 6000,
          });

          // Automatically launch Manual Review modal with the uploaded receipt image
          setManualModalData({
            draftId: result.draftId,
            imageUrl: result.imageUrl,
            thumbnailUrl: result.thumbnailUrl,
            invoiceNumber: result.partialData?.invoiceNumber || '',
            vendorName: result.partialData?.vendorName || '',
            invoiceDate: result.partialData?.invoiceDate || '',
            invoiceAmount: result.partialData?.invoiceAmount || 0,
            gstNumbers: result.partialData?.gstNumbers || [],
            lineItems: []
          });
          setIsManualModalOpen(true);
        } else {
          // Handle processing error
          setFiles(prev => prev.map(f => 
            f.id === fileId ? {
              ...f,
              progress: 100,
              status: "error",
              error: result.error || "Processing failed"
            } : f
          ));
          
          toast.error(`Failed to process ${file.name}: ${result.error || "Processing error"}`);
        }

      } catch (error: any) {
        console.error('Upload error:', error);
        
        setFiles(prev => prev.map(f => 
          f.id === fileId ? {
            ...f,
            progress: 100,
            status: "error",
            error: `Network error: ${error.message || 'Unknown error'}`
          } : f
        ));
        
        toast.error(`Network error uploading ${file.name}: ${error.message || 'Unknown error'}`);
      }
    }
  };

  const getStatusIcon = (status: UploadedFile["status"]) => {
    switch (status) {
      case "completed":
        return <CheckCircle className="h-5 w-5 text-green-500" />;
      case "needs_manual_review":
        return <AlertCircle className="h-5 w-5 text-amber-500" />;
      case "error":
        return <AlertCircle className="h-5 w-5 text-red-500" />;
      case "processing":
        return <Clock className="h-5 w-5 text-blue-500" />;
    }
  };

  const getStatusText = (status: UploadedFile["status"]) => {
    switch (status) {
      case "completed":
        return "Completed";
      case "needs_manual_review":
        return "Needs Review";
      case "error":
        return "Error";
      case "processing":
        return "Processing";
    }
  };

  const openReviewModal = (file: UploadedFile) => {
    setManualModalData({
      draftId: file.draftId || file.id,
      imageUrl: file.imageUrl || file.extractedData?.imageUrl,
      thumbnailUrl: file.thumbnailUrl || file.extractedData?.thumbnailUrl,
      invoiceNumber: file.extractedData?.invoiceNumber !== 'Unknown' ? file.extractedData?.invoiceNumber : '',
      vendorName: file.extractedData?.vendorName !== 'Unknown' ? file.extractedData?.vendorName : '',
      invoiceAmount: file.extractedData?.invoiceAmount || 0,
      invoiceDate: file.extractedData?.invoiceDate !== 'Unknown' ? file.extractedData?.invoiceDate : '',
      gstNumbers: file.extractedData?.gstNumbers || [],
      gstRate: file.extractedData?.gstRate !== 'Unknown' ? file.extractedData?.gstRate : '18%',
      hsnNumber: file.extractedData?.hsnNumber !== 'Unknown' ? file.extractedData?.hsnNumber : '',
    });
    setIsManualModalOpen(true);
  };

  const showDetails = (file: UploadedFile) => {
    if (file.extractedData) {
      const data = file.extractedData;
      
      // Create detailed compliance report
      const complianceDetails = `
🤖 FINTEL AI - COMPLETE COMPLIANCE REPORT
==========================================

📋 BASIC EXTRACTION:
• Invoice Number: ${data.invoiceNumber}
• Vendor: ${data.vendorName}
• Amount: ₹${data.invoiceAmount?.toLocaleString() || 'Not found'}
• Date: ${data.invoiceDate}
• GST Numbers: ${data.gstNumbers?.join(', ') || 'None'}

📊 COMPLIANCE SCORING:
• Overall Score: ${data.complianceScore?.toFixed(1) || 0}%
• Status: ${data.complianceStatus || 'Unknown'}
• Checks Passed: ${data.checksPassedCount || 0}/${data.totalChecksCount || 12}
• Risk Level: ${data.riskLevel || 'Unknown'}

🔍 ENHANCED EXTRACTION:
• HSN/SAC Codes: ${data.hsnSacCodes?.join(', ') || 'None'}
• Items: ${data.itemDescriptions?.join(', ') || 'None'}
• OCR Confidence: ${data.ocrConfidence?.toFixed(1) || 0}%

🚨 ANOMALIES DETECTED:
${data.anomaliesDetected?.length > 0 ? 
  data.anomaliesDetected.map(a => `• ${a}`).join('\n') : 
  '• No anomalies detected'}

✅ VALIDATION RESULTS:
• GST Validation: ${data.gstValidations?.length > 0 ? 
  data.gstValidations.map(g => g.valid ? '✅ Valid' : '❌ Invalid').join(', ') : 
  'Not checked'}
• HSN Validation: ${data.hsnValidations?.length > 0 ? 
  data.hsnValidations.map(h => h.is_correct ? '✅ Correct' : '❌ Incorrect').join(', ') : 
  'Not checked'}
• Arithmetic Check: ${data.arithmeticCheck?.overall_accurate ? '✅ Accurate' : '❌ Error detected'}
• Duplicate Check: ${data.duplicateCheck?.length > 0 ? '🚨 Duplicate found' : '✅ No duplicates'}

💰 PRICE ANALYSIS:
${data.priceAnalysis?.length > 0 ? 
  data.priceAnalysis.map(p => 
    `• ${p.item}: ₹${p.billed_price} (${p.variance_percent > 0 ? '+' : ''}${p.variance_percent?.toFixed(1)}% vs market)`
  ).join('\n') : 
  '• No price analysis available'}

🎯 RISK ASSESSMENT:
• Risk Score: ${data.riskScore || 0}/100
• ML Prediction: ${data.mlPrediction?.is_anomaly ? '🚨 Anomaly detected' : '✅ Normal pattern'}
• Confidence: ${data.mlPrediction?.confidence?.toFixed(1) || 0}%

Processed by: FINTEL AI v2.0 Complete Compliance System
      `;
      
      alert(complianceDetails);
    } else if (file.error) {
      alert(`❌ Processing Error: ${file.error}`);
    } else {
      alert("⏳ Still processing... Please wait.");
    }
  };

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <h1 className="text-3xl font-bold">Upload Invoices</h1>
              {companyName && (
                <Badge variant="secondary" className="text-xs flex items-center gap-1 font-medium">
                  <Building2 className="h-3 w-3" />
                  {companyName}
                </Badge>
              )}
            </div>
            <p className="text-muted-foreground">
              Upload PDF, PNG, or JPEG invoices for AI-powered extraction and compliance validation
            </p>
          </div>
          <Button 
            variant="outline" 
            className="gap-2 self-start sm:self-auto border-dashed hover:border-primary shadow-sm"
            onClick={() => {
              setManualModalData(undefined);
              setIsManualModalOpen(true);
            }}
          >
            <Edit3 className="h-4 w-4" />
            Manual Entry (Fallback)
          </Button>
        </div>

        {/* Upload Zone with Latest Result */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Left: Upload Box */}
          <Card className="p-12 border-2 border-dashed hover:border-primary transition-colors">
            <div
              className="flex flex-col items-center justify-center space-y-4"
              onDrop={handleDrop}
              onDragOver={(e) => e.preventDefault()}
            >
              <div className="p-6 rounded-full bg-primary/10">
                <UploadIcon className="h-12 w-12 text-primary" />
              </div>
              <div className="text-center space-y-2">
                <h3 className="text-xl font-semibold">
                  Drop invoices here or click to browse
                </h3>
                <p className="text-sm text-muted-foreground">
                  Supports PDF, PNG, JPEG • Max 20MB per file
                </p>
              </div>
              <input
                ref={fileInputRef}
                type="file"
                multiple
                accept=".pdf,.png,.jpg,.jpeg"
                className="hidden"
                id="file-upload"
                onChange={handleFileInput}
              />
              <label htmlFor="file-upload">
                <Button asChild>
                  <span>Browse Files</span>
                </Button>
              </label>
            </div>
          </Card>

          {/* Right: Latest Invoice Summary */}
          <Card className="p-6">
            {files.length > 0 && files[0].status === "completed" && files[0].extractedData ? (
              <div>
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-semibold">Latest Invoice</h3>
                  <div className="flex items-center gap-2">
                    {files[0].extractedData.isManualEntry && (
                      <Badge variant="secondary" className="text-xs">
                        Manual Entry
                      </Badge>
                    )}
                    <Badge variant="default" className="bg-green-100 text-green-800">
                      <CheckCircle className="h-3 w-3 mr-1" />
                      Processed
                    </Badge>
                  </div>
                </div>
                <div className="space-y-3">
                  <div className="flex items-center justify-between text-sm">
                    <div className="flex items-center gap-2 truncate">
                      <FileText className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                      <span className="font-medium truncate">{files[0].name}</span>
                    </div>
                    {files[0].imageUrl && (
                      <a 
                        href={`${AI_AGENT_BASE}${files[0].imageUrl}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-xs text-primary hover:underline flex items-center gap-1 font-medium flex-shrink-0 ml-2"
                      >
                        <ImageIcon className="h-3.5 w-3.5" />
                        Receipt Image
                      </a>
                    )}
                  </div>
                  
                  <Card className="p-4 border-l-4 border-l-primary">
                    <h4 className="font-semibold text-base mb-3">Invoice Summary</h4>
                    <div className="space-y-2.5">
                      {/* Vendor */}
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span className="text-sm text-muted-foreground min-w-[80px]">Vendor</span>
                          <span className="font-semibold text-sm">{files[0].extractedData.vendorName}</span>
                        </div>
                        {files[0].extractedData.vendorName !== 'Unknown' ? (
                          <Badge variant="default" className="bg-green-100 text-green-800 text-xs">
                            <CheckCircle className="h-3 w-3 mr-1" />
                            Valid
                          </Badge>
                        ) : (
                          <Badge variant="secondary" className="bg-yellow-100 text-yellow-800 text-xs">
                            <AlertCircle className="h-3 w-3 mr-1" />
                            Missing
                          </Badge>
                        )}
                      </div>

                      {/* Invoice Number */}
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span className="text-sm text-muted-foreground min-w-[80px]">Invoice #</span>
                          <span className="font-semibold text-sm">{files[0].extractedData.invoiceNumber}</span>
                        </div>
                        {files[0].extractedData.invoiceNumber !== 'Unknown' ? (
                          <Badge variant="default" className="bg-green-100 text-green-800 text-xs">
                            <CheckCircle className="h-3 w-3 mr-1" />
                            Valid
                          </Badge>
                        ) : (
                          <Badge variant="secondary" className="bg-yellow-100 text-yellow-800 text-xs">
                            <AlertCircle className="h-3 w-3 mr-1" />
                            Verify
                          </Badge>
                        )}
                      </div>

                      {/* Amount */}
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span className="text-sm text-muted-foreground min-w-[80px]">Amount</span>
                          <span className="font-semibold text-sm">
                            {String(files[0].extractedData.invoiceAmount) !== 'Unknown' && files[0].extractedData.invoiceAmount !== 0 
                              ? `₹${files[0].extractedData.invoiceAmount}` 
                              : '—'}
                          </span>
                        </div>
                        {String(files[0].extractedData.invoiceAmount) !== 'Unknown' && files[0].extractedData.invoiceAmount !== 0 ? (
                          <Badge variant="default" className="bg-green-100 text-green-800 text-xs">
                            <CheckCircle className="h-3 w-3 mr-1" />
                            Valid
                          </Badge>
                        ) : (
                          <Badge variant="secondary" className="bg-yellow-100 text-yellow-800 text-xs">
                            <AlertCircle className="h-3 w-3 mr-1" />
                            Missing
                          </Badge>
                        )}
                      </div>

                      {/* Date */}
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span className="text-sm text-muted-foreground min-w-[80px]">Date</span>
                          <span className="font-semibold text-sm">{files[0].extractedData.invoiceDate !== 'Unknown' ? files[0].extractedData.invoiceDate : '—'}</span>
                        </div>
                        {files[0].extractedData.invoiceDate !== 'Unknown' ? (
                          <Badge variant="default" className="bg-green-100 text-green-800 text-xs">
                            <CheckCircle className="h-3 w-3 mr-1" />
                            Valid
                          </Badge>
                        ) : (
                          <Badge variant="secondary" className="bg-yellow-100 text-yellow-800 text-xs">
                            <AlertCircle className="h-3 w-3 mr-1" />
                            Missing
                          </Badge>
                        )}
                      </div>

                      {/* GST Number */}
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span className="text-sm text-muted-foreground min-w-[80px]">GST</span>
                          <span className="font-semibold text-sm">
                            {files[0].extractedData.gstNumbers && files[0].extractedData.gstNumbers.length > 0 
                              ? files[0].extractedData.gstNumbers[0] 
                              : '—'}
                          </span>
                        </div>
                        {files[0].extractedData.gstNumbers && files[0].extractedData.gstNumbers.length > 0 ? (
                          files[0].extractedData.gstVerification && 
                          files[0].extractedData.gstVerification.length > 0 && 
                          (files[0].extractedData.gstVerification[0]?.is_active === true || 
                           files[0].extractedData.gstVerification[0]?.is_valid === true) ? (
                            <Badge variant="default" className="bg-green-100 text-green-800 text-xs">
                              <CheckCircle className="h-3 w-3 mr-1" />
                              Verified
                            </Badge>
                          ) : files[0].extractedData.gstVerification && 
                              files[0].extractedData.gstVerification.length > 0 && 
                              files[0].extractedData.gstVerification[0]?.is_valid === false ? (
                            <Badge variant="destructive" className="bg-red-100 text-red-800 text-xs">
                              <AlertCircle className="h-3 w-3 mr-1" />
                              Invalid
                            </Badge>
                          ) : (
                            <Badge variant="default" className="bg-green-100 text-green-800 text-xs">
                              <CheckCircle className="h-3 w-3 mr-1" />
                              Verified
                            </Badge>
                          )
                        ) : (
                          <Badge variant="secondary" className="bg-yellow-100 text-yellow-800 text-xs">
                            <AlertCircle className="h-3 w-3 mr-1" />
                            Missing
                          </Badge>
                        )}
                      </div>

                      {/* GST Rate */}
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span className="text-sm text-muted-foreground min-w-[80px]">GST Rate</span>
                          <span className="font-semibold text-sm">
                            {files[0].extractedData.gstRate && files[0].extractedData.gstRate !== 'Unknown'
                              ? files[0].extractedData.gstRate
                              : '—'}
                          </span>
                        </div>
                        {files[0].extractedData.gstRate && files[0].extractedData.gstRate !== 'Unknown' ? (
                          <Badge variant="default" className="bg-green-100 text-green-800 text-xs">
                            <CheckCircle className="h-3 w-3 mr-1" />
                            Found
                          </Badge>
                        ) : (
                          <Badge variant="secondary" className="bg-yellow-100 text-yellow-800 text-xs">
                            <AlertCircle className="h-3 w-3 mr-1" />
                            Missing
                          </Badge>
                        )}
                      </div>

                      {/* HSN Number */}
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span className="text-sm text-muted-foreground min-w-[80px]">HSN</span>
                          <span className="font-semibold text-sm">
                            {files[0].extractedData.hsnNumber && files[0].extractedData.hsnNumber !== 'Unknown'
                              ? files[0].extractedData.hsnNumber
                              : '—'}
                          </span>
                        </div>
                        {files[0].extractedData.hsnNumber && files[0].extractedData.hsnNumber !== 'Unknown' ? (
                          <Badge variant="default" className="bg-green-100 text-green-800 text-xs">
                            <CheckCircle className="h-3 w-3 mr-1" />
                            Found
                          </Badge>
                        ) : (
                          <Badge variant="secondary" className="bg-yellow-100 text-yellow-800 text-xs">
                            <AlertCircle className="h-3 w-3 mr-1" />
                            Missing
                          </Badge>
                        )}
                      </div>

                      {/* Issues Detected */}
                      {files[0].extractedData.anomaliesDetected && files[0].extractedData.anomaliesDetected.length > 0 && (
                        <div className="mt-3 pt-3 border-t">
                          <p className="text-sm font-semibold mb-2">Issues Detected:</p>
                          <ul className="space-y-1">
                            {files[0].extractedData.anomaliesDetected.map((anomaly, idx) => (
                              <li key={idx} className="text-sm text-muted-foreground flex items-start gap-2">
                                <span className="text-destructive mt-0.5">•</span>
                                <span>{anomaly}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  </Card>

                  <Button 
                    className="w-full"
                    onClick={() => showDetails(files[0])}
                  >
                    View Full Details
                  </Button>
                </div>
              </div>
            ) : files.length > 0 && files[0].status === "needs_manual_review" ? (
              <div>
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-semibold">Latest Invoice</h3>
                  <Badge variant="outline" className="border-amber-500 text-amber-700 bg-amber-50">
                    <AlertCircle className="h-3 w-3 mr-1" />
                    Needs Manual Review
                  </Badge>
                </div>
                <div className="space-y-4">
                  <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-sm text-amber-800">
                    <div className="font-semibold mb-1 flex items-center gap-1.5">
                      <AlertCircle className="h-4 w-4 text-amber-600" />
                      AI OCR Breakdown / Low Confidence
                    </div>
                    Confidence fell below 65%. A draft was saved. Please review or correct the invoice manually to complete regulatory compliance checks.
                  </div>

                  <div className="flex items-center justify-between p-3 rounded-lg border bg-muted/30">
                    <div className="flex items-center gap-3">
                      {(files[0].thumbnailUrl || files[0].imageUrl) ? (
                        <img 
                          src={`${AI_AGENT_BASE}${files[0].thumbnailUrl || files[0].imageUrl}`} 
                          alt="Receipt thumbnail" 
                          className="w-12 h-12 object-cover rounded border"
                          onError={(e) => { (e.target as HTMLElement).style.display = 'none'; }}
                        />
                      ) : (
                        <FileText className="h-6 w-6 text-primary" />
                      )}
                      <div>
                        <p className="font-medium text-sm truncate max-w-[200px]">{files[0].name}</p>
                        <p className="text-xs text-muted-foreground">Draft ID: {files[0].draftId || files[0].id}</p>
                      </div>
                    </div>
                    {(files[0].imageUrl) && (
                      <a 
                        href={`${AI_AGENT_BASE}${files[0].imageUrl}`} 
                        target="_blank" 
                        rel="noopener noreferrer"
                        className="text-xs text-primary hover:underline flex items-center gap-1"
                      >
                        <ImageIcon className="h-3.5 w-3.5" />
                        View Receipt
                      </a>
                    )}
                  </div>

                  <Card className="p-4 border-l-4 border-l-amber-500">
                    <h4 className="font-semibold text-sm mb-2.5">Partial Extracted Values</h4>
                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Vendor:</span>
                        <span className="font-medium">{files[0].extractedData?.vendorName || 'Not detected'}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Invoice #:</span>
                        <span className="font-medium">{files[0].extractedData?.invoiceNumber || 'Not detected'}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Amount:</span>
                        <span className="font-medium">
                          {files[0].extractedData?.invoiceAmount ? `₹${files[0].extractedData.invoiceAmount}` : 'Not detected'}
                        </span>
                      </div>
                    </div>
                  </Card>

                  <Button 
                    className="w-full bg-amber-600 hover:bg-amber-700 text-white gap-2"
                    onClick={() => openReviewModal(files[0])}
                  >
                    <Edit3 className="h-4 w-4" />
                    Review & Correct Invoice
                  </Button>
                </div>
              </div>
            ) : files.length > 0 && files[0].status === "processing" ? (
              <div className="flex flex-col items-center justify-center h-full space-y-4">
                <Clock className="h-12 w-12 text-primary animate-spin" />
                <div className="text-center">
                  <h3 className="text-lg font-semibold">Processing Invoice...</h3>
                  <p className="text-sm text-muted-foreground mt-2">{files[0].name}</p>
                  <Progress value={files[0].progress} className="h-2 mt-4" />
                </div>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center h-full text-center space-y-4">
                <div className="p-6 rounded-full bg-muted">
                  <FileText className="h-12 w-12 text-muted-foreground" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold">No Invoice Uploaded</h3>
                  <p className="text-sm text-muted-foreground mt-2">
                    Upload an invoice to see the summary here
                  </p>
                </div>
              </div>
            )}
          </Card>
        </div>


        {/* Past Uploads History */}
        <Card className="p-6">
          <h3 className="text-lg font-semibold mb-4">Past Uploads</h3>
          {isLoadingHistory ? (
            <div className="text-center py-8 text-muted-foreground">
              <Clock className="h-8 w-8 mx-auto mb-2 animate-spin" />
              Loading invoice history...
            </div>
          ) : files.length > 0 ? (
          <div className="space-y-3">
            {files.map((file, index) => (
              <div key={index} className="flex items-center justify-between p-4 rounded-lg border hover:bg-accent/50 transition-colors">
                <div className="flex items-center gap-3 flex-1">
                  {file.thumbnailUrl ? (
                    <img 
                      src={`${AI_AGENT_BASE}${file.thumbnailUrl}`} 
                      alt="Thumbnail" 
                      className="w-10 h-10 object-cover rounded border flex-shrink-0"
                      onError={(e) => { (e.target as HTMLElement).style.display = 'none'; }}
                    />
                  ) : (
                    <div className="w-10 h-10 rounded border bg-muted flex items-center justify-center flex-shrink-0">
                      <FileText className="h-5 w-5 text-primary" />
                    </div>
                  )}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <p className="font-medium truncate">{file.name}</p>
                      {file.extractedData?.isManualEntry && (
                        <Badge variant="outline" className="text-[10px] px-1.5 py-0 h-4">Manual</Badge>
                      )}
                    </div>
                    <div className="flex items-center gap-4 text-sm text-muted-foreground mt-1">
                      {file.extractedData?.vendorName && file.extractedData.vendorName !== 'Unknown' && (
                        <span className="font-medium text-foreground text-xs">
                          {file.extractedData.vendorName}
                        </span>
                      )}
                      {file.extractedData?.invoiceAmount ? (
                        <span className="text-xs">
                          ₹{file.extractedData.invoiceAmount.toLocaleString('en-IN')}
                        </span>
                      ) : null}
                      <span className="flex items-center gap-1 text-xs">
                        <Calendar className="h-3 w-3" />
                        {file.uploadedAt ? new Date(file.uploadedAt).toLocaleDateString('en-IN', { 
                          day: '2-digit', 
                          month: 'short', 
                          year: 'numeric' 
                        }) : file.uploadTime}
                      </span>
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {file.imageUrl && (
                    <a
                      href={`${AI_AGENT_BASE}${file.imageUrl}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="p-2 text-muted-foreground hover:text-primary rounded hover:bg-muted"
                      title="View Receipt Image"
                    >
                      <ImageIcon className="h-4 w-4" />
                    </a>
                  )}

                  {file.status === "needs_manual_review" ? (
                    <>
                      <Badge variant="outline" className="border-amber-500 text-amber-700 bg-amber-50">
                        Needs Review
                      </Badge>
                      <Button 
                        size="sm" 
                        variant="default"
                        className="bg-amber-600 hover:bg-amber-700 text-white gap-1"
                        onClick={() => openReviewModal(file)}
                      >
                        <Edit3 className="h-3.5 w-3.5" />
                        Review
                      </Button>
                    </>
                  ) : file.status === "completed" ? (
                    <>
                      <Badge variant="default" className="bg-green-100 text-green-800">
                        Processed
                      </Badge>
                      <Button 
                        size="sm" 
                        variant="outline"
                        onClick={() => showDetails(file)}
                      >
                        Details
                      </Button>
                    </>
                  ) : file.status === "error" ? (
                    <>
                      <Badge variant="destructive" className="bg-red-100 text-red-800">
                        Error
                      </Badge>
                      <Button 
                        size="sm" 
                        variant="outline"
                        onClick={() => showDetails(file)}
                      >
                        Details
                      </Button>
                    </>
                  ) : (
                    <Badge variant="secondary">
                      Processing
                    </Badge>
                  )}
                </div>
              </div>
            ))}
          </div>
          ) : (
            <div className="text-center py-8 text-muted-foreground">
              No invoices uploaded yet. Upload your first invoice above!
            </div>
          )}
        </Card>

        {/* Auto-sync Options */}
        <Card className="p-6">
          <h3 className="text-lg font-semibold mb-4">Auto-Sync Settings</h3>
          <div className="space-y-3">
            <div className="flex items-center justify-between p-4 rounded-lg border">
              <div>
                <p className="font-medium">Email Inbox Integration</p>
                <p className="text-sm text-muted-foreground">
                  Automatically import invoices from finance@adani.com
                </p>
              </div>
              <Button variant="outline">Configure</Button>
            </div>
            <div className="flex items-center justify-between p-4 rounded-lg border">
              <div>
                <p className="font-medium">Shared Drive Sync</p>
                <p className="text-sm text-muted-foreground">
                  Monitor Google Drive folder for new invoices
                </p>
              </div>
              <Button variant="outline">Connect</Button>
            </div>
          </div>
        </Card>

        {/* Mid-Layer Manual Entry & Review Modal */}
        <ManualInvoiceModal
          isOpen={isManualModalOpen}
          onClose={() => setIsManualModalOpen(false)}
          initialData={manualModalData}
          onSuccess={() => {
            setIsManualModalOpen(false);
            loadInvoiceHistory();
          }}
        />
      </div>
    </DashboardLayout>
  );
};

export default Upload;
