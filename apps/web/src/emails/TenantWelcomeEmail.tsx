import * as React from "react";

export interface TenantWelcomeEmailProps {
  adminName?: string;
  companyName?: string;
  loginUrl?: string;
  phoneNumber?: string;
}

export const TenantWelcomeEmail = ({
  adminName = "Team Member",
  companyName = "Your Logistics Co",
  loginUrl = "https://voxflow-voice-agent.vercel.app/sign-in",
  phoneNumber = "+44 20 7946 0991",
}: TenantWelcomeEmailProps) => {
  return (
    <div style={{ backgroundColor: "#07070f", color: "#e8e0f0", fontFamily: "sans-serif", padding: "40px 20px" }}>
      <div style={{ maxWidth: "600px", margin: "0 auto", backgroundColor: "#0e0e1a", border: "1px solid #28283c", borderRadius: "16px", padding: "36px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "24px" }}>
          <span style={{ fontSize: "20px", fontWeight: "800", color: "#ffffff" }}>
            VOX<span style={{ color: "#ff2d78" }}>FLOW</span>
          </span>
          <span style={{ fontSize: "11px", color: "#00ffcc", fontFamily: "monospace" }}>● OPERATIONAL TRUST</span>
        </div>
        <span style={{ display: "inline-block", padding: "4px 10px", backgroundColor: "rgba(0, 255, 204, 0.1)", color: "#00ffcc", borderRadius: "999px", fontSize: "11px", fontFamily: "monospace", fontWeight: "bold" }}>
          WORKSPACE PROVISIONED
        </span>
        <h1 style={{ color: "#ffffff", fontSize: "24px", margin: "16px 0 12px 0" }}>Welcome to VoxFlow, {adminName}!</h1>
        <p style={{ color: "#cbd5e1", fontSize: "14px", lineHeight: "22px" }}>
          Your autonomous voice operations core for <strong>{companyName}</strong> is live and ready for high-stakes transport and order calls.
        </p>
        <div style={{ backgroundColor: "#141424", border: "1px solid #242438", borderRadius: "10px", padding: "18px", margin: "24px 0" }}>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "8px", fontSize: "13px" }}>
            <span style={{ color: "#94a3b8" }}>Workspace:</span>
            <span style={{ color: "#f8fafc", fontWeight: "bold" }}>{companyName}</span>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "8px", fontSize: "13px" }}>
            <span style={{ color: "#94a3b8" }}>Dialect:</span>
            <span style={{ color: "#f8fafc", fontWeight: "bold" }}>British English (en-GB)</span>
          </div>
          {phoneNumber && (
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: "13px" }}>
              <span style={{ color: "#94a3b8" }}>Assigned Line:</span>
              <span style={{ color: "#00ffcc", fontWeight: "bold", fontFamily: "monospace" }}>{phoneNumber}</span>
            </div>
          )}
        </div>
        <div style={{ textAlign: "center", marginTop: "32px" }}>
          <a href={loginUrl} style={{ display: "inline-block", padding: "12px 28px", backgroundColor: "#ff2d78", color: "#ffffff", textDecoration: "none", fontWeight: "bold", fontSize: "14px", borderRadius: "8px" }}>
            Launch Operations Console →
          </a>
        </div>
      </div>
    </div>
  );
};

export default TenantWelcomeEmail;
