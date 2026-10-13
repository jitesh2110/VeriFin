import React, { useState, useEffect } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Plus, Trash2, ShieldCheck, ZoomIn, ZoomOut, Image as ImageIcon, AlertTriangle } from "lucide-react";
import { toast } from "sonner";
import { fetchWithTenant, AI_AGENT_BASE } from "@/lib/apiClient";

export interface LineItem {
  description: string;
  hsn_code: string;
  quantity: number;
  rate: number;
  amount: number;
}

export interface ManualInvoiceModalProps {
  isOpen: boolean;
  onClose: () => void;
  initialData?: {
    draftId?: string;
    invoiceNumber?: string;
    vendorName?: string;
    invoiceAmount?: number;
    invoiceDate?: string;
    gstNumbers?: string[];
    gstRate?: string;
    hsnNumber?: string;
    lineItems?: LineItem[];
    imageUrl?: string;
    thumbnailUrl?: string;
  };
  onSuccess: (verifiedInvoice: any) => void;
}

export const ManualInvoiceModal: React.FC<ManualInvoiceModalProps> = ({
  isOpen,
  onClose,
  initialData,
  onSuccess,
}) => {
  const [invoiceNumber, setInvoiceNumber] = useState("");
  const [vendorName, setVendorName] = useState("");
  const [invoiceDate, setInvoiceDate] = useState("");
  const [invoiceAmount, setInvoiceAmount] = useState<number>(0);
  const [gstNumber, setGstNumber] = useState("");
  const [gstRate, setGstRate] = useState("18%");
  const [hsnNumber, setHsnNumber] = useState("");
  const [imageUrl, setImageUrl] = useState("");
  const [zoomLevel, setZoomLevel] = useState(1);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const [lineItems, setLineItems] = useState<LineItem[]>([
    { description: "Product/Service Item", hsn_code: "", quantity: 1, rate: 0, amount: 0 },
  ]);

  useEffect(() => {
    if (initialData) {
      setInvoiceNumber(initialData.invoiceNumber && initialData.invoiceNumber !== "Unknown" ? initialData.invoiceNumber : "");
      setVendorName(initialData.vendorName && initialData.vendorName !== "Unknown" ? initialData.vendorName : "");
      setInvoiceDate(initialData.invoiceDate && initialData.invoiceDate !== "Unknown" ? initialData.invoiceDate : new Date().toISOString().split("T")[0]);
      setInvoiceAmount(initialData.invoiceAmount || 0);
      setGstNumber(initialData.gstNumbers && initialData.gstNumbers.length > 0 ? initialData.gstNumbers[0] : "");
      setGstRate(initialData.gstRate || "18%");
      setHsnNumber(initialData.hsnNumber && initialData.hsnNumber !== "Unknown" ? initialData.hsnNumber : "");
      setImageUrl(initialData.imageUrl || "");
      if (initialData.lineItems && initialData.lineItems.length > 0) {
        setLineItems(initialData.lineItems);
      }
    }
  }, [initialData, isOpen]);

  const handleAddItem = () => {
    setLineItems([
      ...lineItems,
      { description: "", hsn_code: hsnNumber || "", quantity: 1, rate: 0, amount: 0 },
    ]);
  };

  const handleRemoveItem = (index: number) => {
    if (lineItems.length <= 1) {
      toast.info("Invoice must have at least one line item.");
      return;
    }
    setLineItems(lineItems.filter((_, i) => i !== index));
  };

  const handleItemChange = (index: number, field: keyof LineItem, value: any) => {
    const updated = [...lineItems];
    updated[index] = { ...updated[index], [field]: value };

    // Auto-calculate amount if quantity or rate changed
    if (field === "quantity" || field === "rate") {
      const q = field === "quantity" ? Number(value) : updated[index].quantity;
      const r = field === "rate" ? Number(value) : updated[index].rate;
      updated[index].amount = Math.round(q * r * 100) / 100;
    }

    setLineItems(updated);

    // Update total amount automatically if sum of items is positive
    const totalSum = updated.reduce((sum, item) => sum + (Number(item.amount) || 0), 0);
    if (totalSum > 0 && invoiceAmount === 0) {
      setInvoiceAmount(totalSum);
    }
  };

  const isGstFormatValid = (gst: string) => {
    return /^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}[Z]{1}[0-9A-Z]{1}$/.test(gst.trim().toUpperCase());
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!invoiceNumber.trim()) {
      toast.error("Please enter an Invoice Number.");
      return;
    }
    if (!vendorName.trim()) {
      toast.error("Please enter Vendor Name.");
      return;
    }
    if (invoiceAmount <= 0) {
      toast.error("Invoice amount must be greater than zero.");
      return;
    }

    setIsSubmitting(true);
    try {
      const payload = {
        invoiceNumber: invoiceNumber.trim(),
        vendorName: vendorName.trim(),
        invoiceDate: invoiceDate || new Date().toISOString().split("T")[0],
        invoiceAmount: Number(invoiceAmount),
        gstNumbers: gstNumber.trim() ? [gstNumber.trim().toUpperCase()] : [],
        gstRate: gstRate || "18%",
        hsnNumber: hsnNumber.trim(),
        hsnSacCodes: [
          ...(hsnNumber.trim() ? [hsnNumber.trim()] : []),
          ...lineItems.map((item) => item.hsn_code).filter(Boolean),
        ],
        lineItems: lineItems.map((item) => ({
          description: item.description || "Invoice Item",
          hsn_code: item.hsn_code || hsnNumber.trim(),
          quantity: Number(item.quantity) || 1,
          rate: Number(item.rate) || 0,
          amount: Number(item.amount) || 0,
        })),
        imageUrl: imageUrl || null,
        thumbnailUrl: initialData?.thumbnailUrl || null,
      };

      const url = initialData?.draftId
        ? `${AI_AGENT_BASE}/api/invoices/${initialData.draftId}/review`
        : `${AI_AGENT_BASE}/api/invoices/manual`;

      const method = initialData?.draftId ? "PUT" : "POST";

      const response = await fetchWithTenant(url, {
        method,
        body: JSON.stringify(payload),
      });

      const result = await response.json();

      if (result.success) {
        toast.success("Invoice successfully verified & saved to company database!");
        onSuccess(result.data);
        onClose();
      } else {
        toast.error(result.error || "Failed to process manual invoice");
      }
    } catch (err: any) {
      console.error("Manual invoice error:", err);
      toast.error(`Network error: ${err.message || "Failed to connect to backend"}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-5xl max-h-[92vh] overflow-y-auto">
        <DialogHeader>
          <div className="flex items-center gap-2">
            <DialogTitle className="text-2xl font-bold flex items-center gap-2">
              <ShieldCheck className="h-6 w-6 text-primary" />
              Manual Invoice Entry & Fallback Review
            </DialogTitle>
            <Badge variant="outline" className="bg-amber-50 text-amber-700 border-amber-300">
              Mid-Layer Fallback
            </Badge>
          </div>
          <DialogDescription>
            If AI OCR encounters low confidence or unreadable scans, key in or correct the receipt data below.
            VeriFin will automatically verify the vendor GSTIN, HSN rates, arithmetic, and fraud patterns.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* Left Column: Receipt Document Preview */}
            <div className="lg:col-span-5 flex flex-col space-y-3">
              <div className="flex items-center justify-between">
                <Label className="text-sm font-semibold flex items-center gap-1.5">
                  <ImageIcon className="h-4 w-4 text-muted-foreground" />
                  Receipt Preview
                </Label>
                {imageUrl && (
                  <div className="flex items-center gap-1">
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => setZoomLevel((z) => Math.min(z + 0.25, 2.5))}
                    >
                      <ZoomIn className="h-4 w-4" />
                    </Button>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => setZoomLevel((z) => Math.max(z - 0.25, 0.75))}
                    >
                      <ZoomOut className="h-4 w-4" />
                    </Button>
                  </div>
                )}
              </div>

              <Card className="flex-1 min-h-[360px] max-h-[460px] overflow-auto flex items-center justify-center p-3 bg-muted/40 border-dashed border-2">
                {imageUrl ? (
                  <div className="transition-transform duration-150 origin-top" style={{ transform: `scale(${zoomLevel})` }}>
                    <img
                      src={imageUrl.startsWith("http") ? imageUrl : `${AI_AGENT_BASE}${imageUrl}`}
                      alt="Invoice Preview"
                      className="max-w-full rounded shadow-sm object-contain"
                    />
                  </div>
                ) : (
                  <div className="text-center p-6 space-y-2 text-muted-foreground">
                    <ImageIcon className="h-10 w-10 mx-auto opacity-40" />
                    <p className="text-sm font-medium">No document image attached</p>
                    <p className="text-xs">Receipt images are automatically compressed to WebP when uploaded.</p>
                  </div>
                )}
              </Card>
            </div>

            {/* Right Column: Invoice Details Form */}
            <div className="lg:col-span-7 space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <Label htmlFor="inv-num">Invoice Number *</Label>
                  <Input
                    id="inv-num"
                    placeholder="e.g. INV-2026-0042"
                    value={invoiceNumber}
                    onChange={(e) => setInvoiceNumber(e.target.value)}
                    required
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="inv-date">Invoice Date *</Label>
                  <Input
                    id="inv-date"
                    type="date"
                    value={invoiceDate}
                    onChange={(e) => setInvoiceDate(e.target.value)}
                    required
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <Label htmlFor="vendor-name">Vendor / Supplier Name *</Label>
                  <Input
                    id="vendor-name"
                    placeholder="e.g. Apex Hardware Pvt Ltd"
                    value={vendorName}
                    onChange={(e) => setVendorName(e.target.value)}
                    required
                  />
                </div>
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between">
                    <Label htmlFor="gst-number">Vendor GSTIN</Label>
                    {gstNumber && (
                      <span className={`text-[11px] ${isGstFormatValid(gstNumber) ? "text-green-600 font-medium" : "text-amber-600"}`}>
                        {isGstFormatValid(gstNumber) ? "✓ Valid Format" : "⚠ 15 chars expected"}
                      </span>
                    )}
                  </div>
                  <Input
                    id="gst-number"
                    placeholder="e.g. 27AAPFU0939F1ZV"
                    value={gstNumber}
                    maxLength={15}
                    onChange={(e) => setGstNumber(e.target.value.toUpperCase())}
                  />
                </div>
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div className="space-y-1.5">
                  <Label htmlFor="total-amount">Total Amount (₹) *</Label>
                  <Input
                    id="total-amount"
                    type="number"
                    step="0.01"
                    placeholder="0.00"
                    value={invoiceAmount || ""}
                    onChange={(e) => setInvoiceAmount(parseFloat(e.target.value) || 0)}
                    required
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="hsn-num">Primary HSN Code</Label>
                  <Input
                    id="hsn-num"
                    placeholder="e.g. 8471"
                    value={hsnNumber}
                    onChange={(e) => setHsnNumber(e.target.value)}
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="gst-rate">GST Rate (%)</Label>
                  <Input
                    id="gst-rate"
                    placeholder="18%"
                    value={gstRate}
                    onChange={(e) => setGstRate(e.target.value)}
                  />
                </div>
              </div>

              {/* Line Items Section */}
              <div className="space-y-2 pt-2">
                <div className="flex items-center justify-between">
                  <Label className="text-sm font-semibold">Line Items & Taxes</Label>
                  <Button type="button" variant="outline" size="sm" onClick={handleAddItem} className="h-7 text-xs">
                    <Plus className="h-3.5 w-3.5 mr-1" /> Add Line Item
                  </Button>
                </div>

                <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
                  {lineItems.map((item, idx) => (
                    <div key={idx} className="grid grid-cols-12 gap-2 items-center bg-muted/30 p-2 rounded-md border text-sm">
                      <div className="col-span-5">
                        <Input
                          placeholder="Description"
                          value={item.description}
                          className="h-8 text-xs"
                          onChange={(e) => handleItemChange(idx, "description", e.target.value)}
                        />
                      </div>
                      <div className="col-span-2">
                        <Input
                          placeholder="HSN"
                          value={item.hsn_code}
                          className="h-8 text-xs"
                          onChange={(e) => handleItemChange(idx, "hsn_code", e.target.value)}
                        />
                      </div>
                      <div className="col-span-2">
                        <Input
                          type="number"
                          placeholder="Qty"
                          value={item.quantity}
                          className="h-8 text-xs"
                          onChange={(e) => handleItemChange(idx, "quantity", e.target.value)}
                        />
                      </div>
                      <div className="col-span-2">
                        <Input
                          type="number"
                          step="0.01"
                          placeholder="Amount"
                          value={item.amount}
                          className="h-8 text-xs"
                          onChange={(e) => handleItemChange(idx, "amount", e.target.value)}
                        />
                      </div>
                      <div className="col-span-1 text-center">
                        <Button
                          type="button"
                          variant="ghost"
                          size="icon"
                          onClick={() => handleRemoveItem(idx)}
                          className="h-8 w-8 text-muted-foreground hover:text-destructive"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>

          <DialogFooter className="gap-2 sm:gap-0 pt-2 border-t">
            <Button type="button" variant="outline" onClick={onClose} disabled={isSubmitting}>
              Cancel
            </Button>
            <Button type="submit" disabled={isSubmitting} className="gap-2">
              <ShieldCheck className="h-4 w-4" />
              {isSubmitting ? "Validating & Saving..." : "Validate & Save to Tenant DB"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
};
