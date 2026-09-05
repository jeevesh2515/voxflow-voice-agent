import * as React from "react";

export interface PasswordResetEmailProps {
  userName?: string;
  resetUrl?: string;
  expiresInMinutes?: number;
}

export const PasswordResetEmail = ({
  userName = "Operator",
  resetUrl = "https://voxflow-voice-agent.vercel.app/reset-password?token=example",
  expiresInMinutes = 60,
}: PasswordResetEmailProps) => {
  return (
    <div style={{ backgroundColor: "#07070f", color: "#e8e0f0", fontFamily: "sans-serif", padding: "40px 20px" }}>
      <div style={{ maxWidth: "600px", margin: "0 auto", backgroundColor: "#0e0e1a", border: "1px solid #28283c", borderRadius: "16px", padding: "36px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "24px" }}>
          <span style={{ fontSize: "20px", fontWeight: "800", color: "#ffffff" }}>
            VOX<span style={{ color: "#ff2d78" }}>FLOW</span>
          </span>
          <span style={{ fontSize: "11px", color: "#ff2d78", fontFamily: "monospace" }}>● SECURITY ACTION</span>
        </div>
        <h1 style={{ color: "#ffffff", fontSize: "24px", margin: "16px 0 12px 0" }}>Reset Your Password</h1>
        <p style={{ color: "#cbd5e1", fontSize: "14px", lineHeight: "22px" }}>
          Hello {userName}, we received a request to reset your console password. Click the button below to securely configure a new credential.
        </p>
        <div style={{ textAlign: "center", margin: "32px 0" }}>
          <a href={resetUrl} style={{ display: "inline-block", padding: "12px 28px", backgroundColor: "#ff2d78", color: "#ffffff", textDecoration: "none", fontWeight: "bold", fontSize: "14px", borderRadius: "8px" }}>
            Reset Password Securely →
          </a>
        </div>
        <div style={{ backgroundColor: "#141424", border: "1px solid #242438", borderRadius: "10px", padding: "16px", fontSize: "12px", color: "#94a3b8" }}>
          This link will expire in {expiresInMinutes} minutes. If you did not initiate this request, no action is needed.
        </div>
      </div>
    </div>
  );
};

export default PasswordResetEmail;
