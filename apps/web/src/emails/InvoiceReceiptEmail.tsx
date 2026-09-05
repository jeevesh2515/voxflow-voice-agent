import * as React from "react";

export interface InvoiceReceiptEmailProps {
  companyName?: string;
  invoiceId?: string;
  amountGbp?: string;
  periodEnd?: string;
  hostedUrl?: string;
  pdfUrl?: string;
}

export const InvoiceReceiptEmail = ({
  companyName = "Your Logistics Co",
  invoiceId = "in_123456789",
  amountGbp = "£149.00",
  periodEnd = "30 Sep 2026",
  hostedUrl = "https://billing.stripe.com/invoice/example",
  pdfUrl = "https://billing.stripe.com/invoice/example/pdf",
}: InvoiceReceiptEmailProps) => {
  return (
    <div style={{ backgroundColor: "#07070f", color: "#e8e0f0", fontFamily: "sans-serif", padding: "40px 20px" }}>
      <div style={{ maxWidth: "600px", margin: "0 auto", backgroundColor: "#0e0e1a", border: "1px solid #28283c", borderRadius: "16px", padding: "36px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "24px" }}>
          <span style={{ fontSize: "20px", fontWeight: "800", color: "#ffffff" }}>
            VOX<span style={{ color: "#ff2d78" }}>FLOW</span>
          </span>
          <span style={{ fontSize: "11px", color: "#00ffcc", fontFamily: "monospace" }}>● PAYMENT CONFIRMED</span>
        </div>
        <h1 style={{ color: "#ffffff", fontSize: "24px", margin: "16px 0 12px 0" }}>Payment Receipt & VAT Invoice</h1>
        <p style={{ color: "#cbd5e1", fontSize: "14px", lineHeight: "22px" }}>
          Thank you for your payment. Your VoxFlow subscription for <strong>{companyName}</strong> is active.
        </p>
        <div style={{ backgroundColor: "#141424", border: "1px solid #242438", borderRadius: "10px", padding: "18px", margin: "24px 0" }}>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "8px", fontSize: "13px" }}>
            <span style={{ color: "#94a3b8" }}>Invoice ID:</span>
            <span style={{ color: "#f8fafc", fontFamily: "monospace" }}>{invoiceId}</span>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "8px", fontSize: "13px" }}>
            <span style={{ color: "#94a3b8" }}>Amount Paid:</span>
            <span style={{ color: "#00ffcc", fontWeight: "bold", fontSize: "15px" }}>{amountGbp}</span>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "8px", fontSize: "13px" }}>
            <span style={{ color: "#94a3b8" }}>VAT:</span>
            <span style={{ color: "#f8fafc" }}>20% UK VAT Included</span>
          </div>
          {periodEnd && (
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: "13px" }}>
              <span style={{ color: "#94a3b8" }}>Current Period End:</span>
              <span style={{ color: "#f8fafc" }}>{periodEnd}</span>
            </div>
          )}
        </div>
        <div style={{ textAlign: "center", marginTop: "24px" }}>
          {hostedUrl && (
            <a href={hostedUrl} style={{ color: "#00ffcc", textDecoration: "none", fontWeight: "bold", fontSize: "13px", marginRight: "16px" }}>
              View Online Receipt ↗
            </a>
          )}
          {pdfUrl && (
            <a href={pdfUrl} style={{ color: "#00ffcc", textDecoration: "none", fontWeight: "bold", fontSize: "13px" }}>
              Download PDF ↗
            </a>
          )}
        </div>
      </div>
    </div>
  );
};

export default InvoiceReceiptEmail;
