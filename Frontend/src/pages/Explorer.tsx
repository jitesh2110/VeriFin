import { useState, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Search, Filter, Download, Eye, CheckCircle, AlertTriangle, XCircle, Loader2 } from "lucide-react";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

interface Invoice {
  id: string;
  invoiceNo: string;
  vendor: string;
  date: string;
  amount: string;
  gstinVendor: string;
  gstinCompany: string;
  accuracy: number;
  riskScore: number;
  flags: string[];
  status: "compliant" | "warning" | "error";
}

const Explorer = () => {
  const [searchParams] = useSearchParams();
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedInvoice, setSelectedInvoice] = useState<Invoice | null>(null);
  const [searchQuery, setSearchQuery] = useState(searchParams.get("search") || "");
  const [statusFilter, setStatusFilter] = useState("all");

  useEffect(() => {
    fetchInvoices();
  }, []);

  const fetchInvoices = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/invoices/history');
      const data = await response.json();
      
      if (data.success && data.invoices) {
        // Transform backend data to frontend format
        const transformedInvoices = data.invoices.map((invoice: any) => {
          // Determine status based on compliance and anomalies
          let status: Invoice['status'] = 'compliant';
          const flags: string[] = [];
          
          // Check for missing or invalid GST
          const gstNumbers = invoice.allGstNumbers || invoice.gst_numbers || invoice.gstNumber;
          console.log(`Invoice ${invoice.invoiceNumber}: GST Numbers =`, gstNumbers);
          if (!gstNumbers || gstNumbers.length === 0 || gstNumbers[0] === 'N/A') {
            console.log(`  → Missing GST detected!`);
            flags.push('Missing GST');
            status = 'error';
          }
          
          // Check GST verification status
          if (invoice.gstVerification && invoice.gstVerification.length > 0) {
            const gstVerif = invoice.gstVerification[0];
            if (gstVerif.success === false || gstVerif.is_valid === false) {
              flags.push('Invalid GST');
              status = 'error';
            } else if (!gstVerif.is_active) {
              flags.push('Inactive GST');
              status = 'warning';
            }
          }
          
          // Check for anomalies in the database
          if (invoice.anomalies && invoice.anomalies.length > 0) {
            invoice.anomalies.forEach((anomaly: any) => {
              // Handle both camelCase and snake_case
              const type = anomaly.anomalyType || anomaly.anomaly_type;
              
              if (type === 'DUPLICATE_INVOICE') flags.push('Duplicate');
              if (type === 'INVALID_GST') flags.push('Invalid GST');
              if (type === 'MISSING_GST') flags.push('Missing GST');
              if (type === 'GST_VENDOR_MISMATCH') flags.push('GST Mismatch');
              if (type === 'INVALID_HSN_SAC') flags.push('Invalid HSN/SAC');
              if (type === 'MISSING_HSN_SAC') flags.push('Missing HSN');
              if (type === 'HSN_GST_RATE_MISMATCH') flags.push('HSN Rate Mismatch');
              if (type === 'UNUSUAL_AMOUNT') flags.push('Price Outlier');
              if (type === 'HSN_PRICE_DEVIATION') flags.push('HSN Deviation');
            });
            if (flags.length > 0 && status === 'compliant') status = 'warning';
          }
          
          // Fallback: Check for missing HSN explicitly if not caught by DB anomalies
          const hsnCodes = invoice.hsnCodes || invoice.hsn_sac_codes || [];
          const hsnNumber = invoice.hsnNumber || invoice.hsn_number;
          if ((!hsnCodes || hsnCodes.length === 0) && (!hsnNumber || hsnNumber === 'Unknown' || hsnNumber === '')) {
            if (!flags.includes('Missing HSN')) {
              flags.push('Missing HSN');
              if (status === 'compliant') status = 'warning';
            }
          }
          
          // Determine status based on compliance score
          const complianceResults = invoice.complianceResults || invoice.compliance_results;
          if (complianceResults) {
            const complianceScore = complianceResults.compliance_score || 0;
            if (complianceScore < 50) {
              status = 'error';
            } else if (complianceScore < 80 && status === 'compliant') {
              status = 'warning';
            }
          }
          
          return {
            id: invoice._id || invoice.id,
            invoiceNo: invoice.invoiceNumber || invoice.invoice_number || 'N/A',
            vendor: invoice.vendorName || invoice.vendor_name || 'Unknown',
            date: invoice.invoiceDate || invoice.invoice_date || 'N/A',
            amount: `₹${(invoice.totalAmount || invoice.total_amount || 0).toLocaleString('en-IN')}`,
            gstinVendor: invoice.allGstNumbers?.[0] || invoice.gst_numbers?.[0] || invoice.gstNumber || 'N/A',
            gstinCompany: 'N/A',
            accuracy: invoice.ocrConfidence || invoice.ocr_confidence || 0,
            riskScore: invoice.complianceResults?.risk_score || invoice.compliance_results?.risk_score || 0,
            flags,
            status,
          };
        });
        
        setInvoices(transformedInvoices);
      }
    } catch (error) {
      console.error('Error fetching invoices:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const getStatusBadge = (status: Invoice["status"]) => {
    const variants = {
      compliant: { variant: "default" as const, label: "Compliant", icon: CheckCircle },
      warning: { variant: "secondary" as const, label: "Warning", icon: AlertTriangle },
      error: { variant: "destructive" as const, label: "Error", icon: XCircle },
    };
    const config = variants[status];
    const Icon = config.icon;
    return (
      <Badge variant={config.variant} className="gap-1">
        <Icon className="h-3 w-3" />
        {config.label}
      </Badge>
    );
  };

  const getRiskColor = (score: number) => {
    if (score < 0.3) return "text-success";
    if (score < 0.6) return "text-warning";
    return "text-destructive";
  };

  if (isLoading) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center h-96">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <span className="ml-2">Loading invoices...</span>
        </div>
      </DashboardLayout>
    );
  }

  const filteredInvoices = invoices.filter(invoice => {
    const matchesSearch = invoice.invoiceNo.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         invoice.vendor.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus = statusFilter === "all" || invoice.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const exportToExcel = async () => {
    try {
      const XLSX = await import('xlsx');
      
      const exportData = filteredInvoices.map(inv => ({
        'Invoice No': inv.invoiceNo,
        'Vendor': inv.vendor,
        'Date': inv.date,
        'Amount': inv.amount,
        'Vendor GSTIN': inv.gstinVendor,
        'Status': inv.status,
        'Issues': inv.flags.join(', ') || 'None',
        'Risk Score': inv.riskScore,
        'Accuracy': `${inv.accuracy}%`
      }));

      const ws = XLSX.utils.json_to_sheet(exportData);
      const wb = XLSX.utils.book_new();
      XLSX.utils.book_append_sheet(wb, ws, 'Invoices');
      
      const fileName = `invoice_explorer_${new Date().toISOString().split('T')[0]}.xlsx`;
      XLSX.writeFile(wb, fileName);
    } catch (error) {
      console.error('Export failed:', error);
    }
  };

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold mb-2">Invoice Explorer</h1>
            <p className="text-muted-foreground">
              Search, filter, and manage all processed invoices with compliance issues
            </p>
          </div>
          <Button className="gap-2" onClick={exportToExcel}>
            <Download className="h-4 w-4" />
            Export Data
          </Button>
        </div>

        {/* Filters */}
        <Card className="p-6">
          <div className="grid gap-4 md:grid-cols-4">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search invoices..."
                className="pl-10"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger>
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Status</SelectItem>
                <SelectItem value="compliant">Compliant</SelectItem>
                <SelectItem value="warning">Warning</SelectItem>
                <SelectItem value="error">Error</SelectItem>
              </SelectContent>
            </Select>
            <Select>
              <SelectTrigger>
                <SelectValue placeholder="Date Range" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="7">Last 7 days</SelectItem>
                <SelectItem value="30">Last 30 days</SelectItem>
                <SelectItem value="90">Last 90 days</SelectItem>
              </SelectContent>
            </Select>
            <Button variant="outline" className="gap-2">
              <Filter className="h-4 w-4" />
              More Filters
            </Button>
          </div>
        </Card>

        {/* Table */}
        <Card>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Invoice No</TableHead>
                <TableHead>Vendor</TableHead>
                <TableHead>Date</TableHead>
                <TableHead>Amount</TableHead>
                <TableHead>Vendor GSTIN</TableHead>
                <TableHead>Issues/Flags</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredInvoices.map((invoice) => (
                <TableRow key={invoice.id} className="cursor-pointer hover:bg-muted/50">
                  <TableCell className="font-medium">{invoice.invoiceNo}</TableCell>
                  <TableCell>{invoice.vendor}</TableCell>
                  <TableCell>{invoice.date}</TableCell>
                  <TableCell className="font-semibold">{invoice.amount}</TableCell>
                  <TableCell>
                    <span className="font-mono text-xs">{invoice.gstinVendor}</span>
                  </TableCell>
                  <TableCell>
                    {invoice.flags.length > 0 ? (
                      <div className="flex flex-wrap gap-1">
                        {invoice.flags.map((flag, idx) => (
                          <Badge key={idx} variant="destructive" className="text-xs">
                            {flag}
                          </Badge>
                        ))}
                      </div>
                    ) : (
                      <Badge variant="default" className="text-xs gap-1">
                        <CheckCircle className="h-3 w-3" />
                        No Issues
                      </Badge>
                    )}
                  </TableCell>
                  <TableCell>
                    <Button
                      size="sm"
                      variant="ghost"
                      className="gap-2"
                      onClick={() => setSelectedInvoice(invoice)}
                    >
                      <Eye className="h-4 w-4" />
                      View
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
      </div>

      {/* Detail Sheet */}
      <Sheet open={!!selectedInvoice} onOpenChange={() => setSelectedInvoice(null)}>
        <SheetContent className="w-full sm:max-w-2xl overflow-y-auto">
          <SheetHeader>
            <SheetTitle>Invoice Details</SheetTitle>
            <SheetDescription>
              {selectedInvoice?.invoiceNo} • {selectedInvoice?.vendor}
            </SheetDescription>
          </SheetHeader>

          {selectedInvoice && (
            <Tabs defaultValue="extracted" className="mt-6">
              <TabsList className="grid w-full grid-cols-3">
                <TabsTrigger value="extracted">Extracted Data</TabsTrigger>
                <TabsTrigger value="compliance">Compliance</TabsTrigger>
                <TabsTrigger value="audit">Audit Trail</TabsTrigger>
              </TabsList>

              <TabsContent value="extracted" className="space-y-4 mt-6">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm text-muted-foreground mb-1">Invoice Number</p>
                    <p className="font-medium">{selectedInvoice.invoiceNo}</p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground mb-1">Invoice Date</p>
                    <p className="font-medium">{selectedInvoice.date}</p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground mb-1">Invoice Amount</p>
                    <p className="font-medium text-lg">{selectedInvoice.amount}</p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground mb-1">Extraction Accuracy</p>
                    <p className="font-medium">{selectedInvoice.accuracy}%</p>
                  </div>
                  <div className="col-span-2">
                    <p className="text-sm text-muted-foreground mb-1">Vendor GSTIN</p>
                    <p className="font-mono text-sm">{selectedInvoice.gstinVendor}</p>
                  </div>
                  <div className="col-span-2">
                    <p className="text-sm text-muted-foreground mb-1">Company GSTIN</p>
                    <p className="font-mono text-sm">{selectedInvoice.gstinCompany}</p>
                  </div>
                </div>
              </TabsContent>

              <TabsContent value="compliance" className="space-y-4 mt-6">
                {selectedInvoice.flags.map((flag, index) => (
                  <Card key={index} className="p-4 border-l-4 border-l-warning">
                    <div className="flex items-start gap-3">
                      <AlertTriangle className="h-5 w-5 text-warning mt-0.5" />
                      <div>
                        <h4 className="font-semibold mb-1">{flag}</h4>
                        <p className="text-sm text-muted-foreground">
                          This invoice has been flagged for manual review
                        </p>
                      </div>
                    </div>
                  </Card>
                ))}
                {selectedInvoice.flags.length === 0 && (
                  <Card className="p-6 border-l-4 border-l-success">
                    <div className="flex items-center gap-3">
                      <CheckCircle className="h-6 w-6 text-success" />
                      <p className="font-medium">All compliance checks passed</p>
                    </div>
                  </Card>
                )}
              </TabsContent>

              <TabsContent value="audit" className="space-y-3 mt-6">
                <div className="space-y-3">
                  <div className="flex gap-3">
                    <div className="w-2 bg-success rounded-full" />
                    <div className="flex-1 pb-4">
                      <p className="text-sm font-medium mb-1">File Uploaded</p>
                      <p className="text-xs text-muted-foreground">by Finance Team • 10:20 AM</p>
                    </div>
                  </div>
                  <div className="flex gap-3">
                    <div className="w-2 bg-primary rounded-full" />
                    <div className="flex-1 pb-4">
                      <p className="text-sm font-medium mb-1">Data Extracted</p>
                      <p className="text-xs text-muted-foreground">Accuracy: {selectedInvoice.accuracy}% • 10:21 AM</p>
                    </div>
                  </div>
                  <div className="flex gap-3">
                    <div className="w-2 bg-primary rounded-full" />
                    <div className="flex-1 pb-4">
                      <p className="text-sm font-medium mb-1">GST Validated</p>
                      <p className="text-xs text-muted-foreground">10:22 AM</p>
                    </div>
                  </div>
                  {selectedInvoice.flags.length > 0 && (
                    <div className="flex gap-3">
                      <div className="w-2 bg-warning rounded-full" />
                      <div className="flex-1">
                        <p className="text-sm font-medium mb-1">Anomalies Detected</p>
                        <p className="text-xs text-muted-foreground">10:23 AM</p>
                      </div>
                    </div>
                  )}
                </div>
              </TabsContent>
            </Tabs>
          )}
        </SheetContent>
      </Sheet>
    </DashboardLayout>
  );
};

export default Explorer;