import * as React from "react";

export interface EscalationSummaryEmailProps {
  companyName?: string;
  escalationId?: string;
  callerPhone?: string;
  reason?: string;
  priority?: "low" | "medium" | "high" | "urgent";
  dashboardUrl?: string;
}

export const EscalationSummaryEmail = ({
  companyName = "Your Logistics Co",
  escalationId = "esc_991823",
  callerPhone = "+44 7911 123456",
  reason = "Caller requested human supervisor after second failed dock appointment lookup.",
  priority = "high",
  dashboardUrl = "https://voxflow-voice-agent.vercel.app/dashboard/escalations",
}: EscalationSummaryEmailProps) => {
  const isUrgent = priority === "urgent" || priority === "high";
  const badgeColor = isUrgent ? "#ff4444" : "#ffe04a";

  return (
    <div style={{ backgroundColor: "#07070f", color: "#e8e0f0", fontFamily: "sans-serif", padding: "40px 20px" }}>
      <div style={{ maxWidth: "600px", margin: "0 auto", backgroundColor: "#0e0e1a", border: "1px solid #28283c", borderRadius: "16px", padding: "36px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "24px" }}>
          <span style={{ fontSize: "20px", fontWeight: "800", color: "#ffffff" }}>
            VOX<span style={{ color: "#ff2d78" }}>FLOW</span>
          </span>
          <span style={{ fontSize: "11px", color: badgeColor, fontFamily: "monospace" }}>● OPERATOR ESCALATION</span>
        </div>
        <h1 style={{ color: "#ffffff", fontSize: "24px", margin: "16px 0 12px 0" }}>Human Operator Required</h1>
        <p style={{ color: "#cbd5e1", fontSize: "14px", lineHeight: "22px" }}>
          A voice session for <strong>{companyName}</strong> requires immediate human operator attention.
        </p>
        <div style={{ backgroundColor: "#141424", border: `1px solid ${badgeColor}`, borderLeft: `4px solid ${badgeColor}`, borderRadius: "10px", padding: "18px", margin: "24px 0" }}>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "8px", fontSize: "13px" }}>
            <span style={{ color: "#94a3b8" }}>Escalation ID:</span>
            <span style={{ color: "#f8fafc", fontFamily: "monospace" }}>{escalationId}</span>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "8px", fontSize: "13px" }}>
            <span style={{ color: "#94a3b8" }}>Caller Number:</span>
            <span style={{ color: "#00ffcc", fontFamily: "monospace" }}>{callerPhone}</span>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "8px", fontSize: "13px" }}>
            <span style={{ color: "#94a3b8" }}>Priority:</span>
            <span style={{ color: badgeColor, fontWeight: "bold", textTransform: "uppercase" }}>{priority}</span>
          </div>
          <div style={{ marginTop: "12px", borderTop: "1px solid #28283c", paddingTop: "8px" }}>
            <span style={{ color: "#94a3b8", fontSize: "12px", display: "block", marginBottom: "4px" }}>Reason:</span>
            <span style={{ color: "#f8fafc", fontSize: "13px", lineHeight: "18px" }}>{reason}</span>
          </div>
        </div>
        <div style={{ textAlign: "center", marginTop: "32px" }}>
          <a href={dashboardUrl} style={{ display: "inline-block", padding: "12px 28px", backgroundColor: badgeColor, color: "#0e0e1a", textDecoration: "none", fontWeight: "bold", fontSize: "14px", borderRadius: "8px" }}>
            Resolve in Escalation Queue →
          </a>
        </div>
      </div>
    </div>
  );
};

export default EscalationSummaryEmail;
