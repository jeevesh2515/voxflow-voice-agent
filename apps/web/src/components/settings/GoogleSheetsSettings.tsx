"use client";

import { useState } from "react";
import useSWR from "swr";
import {
  FileSpreadsheet,
  ExternalLink,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  Unlink,
  Link2,
  Copy,
  Check,
  ShieldCheck,
  Zap,
  Info,
  Layers,
  Sparkles,
  Lock,
} from "lucide-react";
import { api } from "@/lib/api";
import { useTenant } from "@/lib/tenant-context";
import { TenantGoogleSheetsConfig, GoogleSheetsTestResult } from "@/lib/types";

interface GoogleSheetsSettingsProps {
  embedded?: boolean;
}

export default function GoogleSheetsSettings({ embedded = false }: GoogleSheetsSettingsProps) {
  const { activeTenantId, activeTenant } = useTenant();
  const isOwner = activeTenant?.role === "owner";

  // SWR for fetching tenant sheet config
  const {
    data: sheetConfig,
    error,
    isLoading,
    mutate,
  } = useSWR<TenantGoogleSheetsConfig>(
    activeTenantId ? ["tenant-google-sheets", activeTenantId] : null,
    () => api.googleSheets.getConfig(activeTenantId)
  );

  // State
  const [modalOpen, setModalOpen] = useState(false);
  const [sheetInput, setSheetInput] = useState("");
  const [sheetName, setSheetName] = useState("");
  const [callTab, setCallTab] = useState("Call Log");
  const [emailTab, setEmailTab] = useState("Email Log");
  const [autoHeaders, setAutoHeaders] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isTesting, setIsTesting] = useState(false);
  const [isDisconnecting, setIsDisconnecting] = useState(false);
  const [testResult, setTestResult] = useState<GoogleSheetsTestResult | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [copiedEmail, setCopiedEmail] = useState(false);
  const [copiedId, setCopiedId] = useState(false);

  // Copy helper
  const handleCopy = (text: string, type: "email" | "id") => {
    navigator.clipboard.writeText(text);
    if (type === "email") {
      setCopiedEmail(true);
      setTimeout(() => setCopiedEmail(false), 2000);
    } else {
      setCopiedId(true);
      setTimeout(() => setCopiedId(false), 2000);
    }
  };

  // Connect Handler
  const handleConnect = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!sheetInput.trim()) {
      setErrorMessage("Please enter a Google Spreadsheet URL or Sheet ID.");
      return;
    }
    setErrorMessage(null);
    setIsSubmitting(true);

    try {
      await api.googleSheets.connect(activeTenantId, {
        sheet_url_or_id: sheetInput.trim(),
        sheet_name: sheetName.trim() || undefined,
        call_tab: callTab.trim() || "Call Log",
        email_tab: emailTab.trim() || "Email Log",
        auto_create_headers: autoHeaders,
      });
      await mutate();
      setModalOpen(false);
      setSheetInput("");
      setSheetName("");
      setTestResult(null);
    } catch (err: any) {
      setErrorMessage(err.message || "Failed to connect spreadsheet. Please verify access.");
    } finally {
      setIsSubmitting(false);
    }
  };

  // Live Test Handler
  const handleTestConnection = async () => {
    setIsTesting(true);
    setTestResult(null);
    try {
      const res = await api.googleSheets.test(activeTenantId);
      setTestResult(res);
      await mutate();
    } catch (err: any) {
      setTestResult({
        ok: false,
        error: "test_failed",
        detail: err.message || "Unable to reach Google Sheets API.",
      });
    } finally {
      setIsTesting(false);
    }
  };

  // Disconnect Handler
  const handleDisconnect = async () => {
    if (!confirm("Are you sure you want to disconnect this Google Spreadsheet? Call logs will no longer sync to this sheet.")) {
      return;
    }
    setIsDisconnecting(true);
    try {
      await api.googleSheets.disconnect(activeTenantId);
      await mutate();
      setTestResult(null);
    } catch (err: any) {
      alert("Failed to disconnect: " + (err.message || "Unknown error"));
    } finally {
      setIsDisconnecting(false);
    }
  };

  const isConnected = sheetConfig?.is_connected;
  const serviceAccount = sheetConfig?.service_account_email;

  return (
    <div
      className={`rounded-2xl border border-slate-800 bg-gradient-to-b from-slate-900/90 to-slate-950/90 backdrop-blur-xl p-6 shadow-2xl relative overflow-hidden ${
        embedded ? "my-4" : ""
      }`}
    >
      {/* Background ambient glow */}
      <div className="absolute -top-24 -right-24 w-60 h-60 bg-emerald-500/10 rounded-full blur-3xl pointer-events-none" />

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-slate-800/80">
        <div className="flex items-center gap-3.5">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-tr from-emerald-600 to-teal-500 p-0.5 shadow-lg shadow-emerald-950/40">
            <div className="w-full h-full bg-slate-950/90 rounded-[10px] flex items-center justify-center">
              <FileSpreadsheet className="w-6 h-6 text-emerald-400" />
            </div>
          </div>
          <div>
            <div className="flex items-center gap-2.5">
              <h3 className="text-lg font-bold text-white tracking-tight">
                Google Sheets Integration
              </h3>
              {isConnected ? (
                <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                  Active Mirror
                </span>
              ) : (
                <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-800/80 text-slate-400 border border-slate-700/50">
                  <span className="w-1.5 h-1.5 rounded-full bg-slate-500" />
                  Not Connected
                </span>
              )}
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Stream live call outcome logs, satisfaction ratings, and automated email records into your own Google Spreadsheet.
            </p>
          </div>
        </div>

        {/* Action Button */}
        <div className="flex items-center gap-2">
          {isConnected ? (
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={handleTestConnection}
                disabled={isTesting}
                className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-slate-800/90 hover:bg-slate-700 text-xs font-semibold text-slate-200 border border-slate-700 transition shadow-sm active:scale-[0.98] disabled:opacity-50"
              >
                <RefreshCw className={`w-3.5 h-3.5 text-emerald-400 ${isTesting ? "animate-spin" : ""}`} />
                {isTesting ? "Testing..." : "Test Connection"}
              </button>
              {isOwner && (
                <>
                  <button
                    type="button"
                    onClick={() => {
                      setSheetInput(sheetConfig?.spreadsheet_url || sheetConfig?.google_sheet_id || "");
                      setSheetName(sheetConfig?.google_sheet_name || "");
                      setCallTab(sheetConfig?.google_sheet_tab || "Call Log");
                      setEmailTab(sheetConfig?.google_sheet_email_tab || "Email Log");
                      setModalOpen(true);
                    }}
                    className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-emerald-600/20 hover:bg-emerald-600/30 text-xs font-semibold text-emerald-300 border border-emerald-500/30 transition active:scale-[0.98]"
                  >
                    <Link2 className="w-3.5 h-3.5" />
                    Configure
                  </button>
                  <button
                    type="button"
                    onClick={handleDisconnect}
                    disabled={isDisconnecting}
                    className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl bg-red-950/30 hover:bg-red-900/40 text-xs font-medium text-red-400 border border-red-800/30 transition active:scale-[0.98] disabled:opacity-50"
                    title="Disconnect Google Sheet"
                  >
                    <Unlink className="w-3.5 h-3.5" />
                  </button>
                </>
              )}
            </div>
          ) : (
            isOwner ? (
              <button
                type="button"
                onClick={() => setModalOpen(true)}
                className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-xs font-bold text-white shadow-lg shadow-emerald-900/30 transition active:scale-[0.98]"
              >
                <Sparkles className="w-3.5 h-3.5" />
                Connect Your Google Sheet
              </button>
            ) : (
              <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800/60 border border-slate-700 text-xs text-slate-400">
                <Lock className="w-3.5 h-3.5 text-slate-500" />
                Owner access required to connect
              </div>
            )
          )}
        </div>
      </div>

      {/* Main Body */}
      <div className="mt-6">
        {isConnected ? (
          <div className="space-y-4">
            {/* Connected Sheet Card */}
            <div className="p-4 rounded-xl bg-slate-950/60 border border-emerald-500/20 flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div className="flex items-start gap-3.5">
                <div className="p-2.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 mt-0.5">
                  <CheckCircle2 className="w-5 h-5" />
                </div>
                <div>
                  <h4 className="text-sm font-semibold text-white flex items-center gap-2">
                    {sheetConfig?.google_sheet_name || "Enterprise Workspace Call Log"}
                  </h4>
                  <div className="flex flex-wrap items-center gap-2 mt-1.5 text-xs text-slate-400">
                    <span className="font-mono bg-slate-900 px-2 py-0.5 rounded border border-slate-800">
                      ID: {sheetConfig?.google_sheet_id?.slice(0, 16)}...
                    </span>
                    <button
                      type="button"
                      onClick={() => handleCopy(sheetConfig?.google_sheet_id || "", "id")}
                      className="text-slate-400 hover:text-slate-200 transition"
                      title="Copy Sheet ID"
                    >
                      {copiedId ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                    </button>
                    <span>•</span>
                    <span>Call Tab: <strong className="text-slate-200">{sheetConfig?.google_sheet_tab}</strong></span>
                    <span>•</span>
                    <span>Email Tab: <strong className="text-slate-200">{sheetConfig?.google_sheet_email_tab}</strong></span>
                  </div>
                </div>
              </div>

              {/* Open in Google Sheets Button */}
              {sheetConfig?.spreadsheet_url && (
                <a
                  href={sheetConfig.spreadsheet_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center justify-center gap-1.5 px-3.5 py-2 rounded-xl bg-emerald-500/10 hover:bg-emerald-500/20 text-xs font-semibold text-emerald-300 border border-emerald-500/30 transition shrink-0"
                >
                  <ExternalLink className="w-3.5 h-3.5" />
                  Open in Google Sheets
                </a>
              )}
            </div>

            {/* Live Test Diagnostic Output */}
            {testResult && (
              <div
                className={`p-3.5 rounded-xl border text-xs flex items-start gap-3 ${
                  testResult.ok
                    ? "bg-emerald-950/20 border-emerald-500/30 text-emerald-300"
                    : "bg-red-950/20 border-red-500/30 text-red-300"
                }`}
              >
                {testResult.ok ? (
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                ) : (
                  <AlertCircle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
                )}
                <div className="space-y-1">
                  <div className="font-semibold">
                    {testResult.ok
                      ? `Preflight Success • ${testResult.title || "Sheet Connected"} (${testResult.latency_ms}ms)`
                      : `Preflight Error • ${testResult.error}`}
                  </div>
                  <p className="text-slate-300">{testResult.detail || testResult.message}</p>
                  {testResult.tabs && testResult.tabs.length > 0 && (
                    <div className="text-[11px] text-slate-400 flex items-center gap-1 pt-1">
                      <Layers className="w-3 h-3" />
                      Detected Tabs: {testResult.tabs.join(", ")}
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        ) : (
          /* Not Connected / Onboarding Guide */
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Step 1 */}
              <div className="p-4 rounded-xl bg-slate-950/50 border border-slate-800 flex flex-col justify-between">
                <div>
                  <div className="flex items-center gap-2 text-xs font-bold text-emerald-400 uppercase tracking-wider">
                    <span className="w-5 h-5 rounded-full bg-emerald-500/20 flex items-center justify-center text-[10px]">1</span>
                    Share With Service Account
                  </div>
                  <p className="text-xs text-slate-400 mt-2">
                    Create or open your Google Spreadsheet, click <strong>Share</strong>, and add our automation service account with <strong>Editor</strong> permissions:
                  </p>
                </div>
                <div className="mt-3 flex items-center justify-between p-2.5 rounded-lg bg-slate-900 border border-slate-800">
                  <span className="text-xs font-mono text-slate-300 truncate max-w-[240px]">
                    {serviceAccount || "voxflow-sheets-writer@voxflow-agent.iam.gserviceaccount.com"}
                  </span>
                  <button
                    type="button"
                    onClick={() =>
                      handleCopy(
                        serviceAccount || "voxflow-sheets-writer@voxflow-agent.iam.gserviceaccount.com",
                        "email"
                      )
                    }
                    className="inline-flex items-center gap-1 text-xs text-emerald-400 hover:text-emerald-300 font-semibold px-2 py-1 rounded bg-emerald-500/10 transition"
                  >
                    {copiedEmail ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                    {copiedEmail ? "Copied" : "Copy"}
                  </button>
                </div>
              </div>

              {/* Step 2 */}
              <div className="p-4 rounded-xl bg-slate-950/50 border border-slate-800 flex flex-col justify-between">
                <div>
                  <div className="flex items-center gap-2 text-xs font-bold text-teal-400 uppercase tracking-wider">
                    <span className="w-5 h-5 rounded-full bg-teal-500/20 flex items-center justify-center text-[10px]">2</span>
                    Connect & Auto-Provision
                  </div>
                  <p className="text-xs text-slate-400 mt-2">
                    Paste your spreadsheet URL or ID. VoxFlow will verify read/write access and automatically bootstrap <strong>Call Log</strong> and <strong>Email Log</strong> headers with formatted columns.
                  </p>
                </div>
                <div className="mt-3">
                  {isOwner ? (
                    <button
                      type="button"
                      onClick={() => setModalOpen(true)}
                      className="w-full py-2.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-white border border-slate-700 flex items-center justify-center gap-2 transition"
                    >
                      <Link2 className="w-3.5 h-3.5 text-emerald-400" />
                      Paste URL & Connect
                    </button>
                  ) : (
                    <div className="text-center py-2 text-xs text-slate-500">
                      Workspace Owner can connect this spreadsheet
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Connect / Edit Modal */}
      {modalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in">
          <div className="w-full max-w-lg rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-2xl">
            <div className="flex items-center justify-between pb-4 border-b border-slate-800">
              <div className="flex items-center gap-2.5">
                <FileSpreadsheet className="w-5 h-5 text-emerald-400" />
                <h3 className="text-base font-bold text-white">
                  {isConnected ? "Reconfigure Google Spreadsheet" : "Connect Google Spreadsheet"}
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setModalOpen(false)}
                className="text-slate-400 hover:text-white text-sm"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleConnect} className="mt-4 space-y-4">
              {errorMessage && (
                <div className="p-3 rounded-xl bg-red-950/40 border border-red-500/30 text-red-300 text-xs flex items-start gap-2">
                  <AlertCircle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
                  <span>{errorMessage}</span>
                </div>
              )}

              {/* Sheet URL or ID */}
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Google Spreadsheet URL or ID <span className="text-red-400">*</span>
                </label>
                <input
                  type="text"
                  required
                  placeholder="https://docs.google.com/spreadsheets/d/1BxiMVs0X.../edit or Sheet ID"
                  value={sheetInput}
                  onChange={(e) => setSheetInput(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-700 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500 transition"
                />
                <p className="text-[11px] text-slate-400 mt-1">
                  Paste the browser link from your Google Sheet directly.
                </p>
              </div>

              {/* Custom Sheet Name */}
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Workspace Sheet Label (Optional)
                </label>
                <input
                  type="text"
                  placeholder="e.g. Varun Beverages - Production Mirror"
                  value={sheetName}
                  onChange={(e) => setSheetName(e.target.value)}
                  className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-700 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500 transition"
                />
              </div>

              {/* Tab Configuration */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">
                    Call Log Tab Name
                  </label>
                  <input
                    type="text"
                    value={callTab}
                    onChange={(e) => setCallTab(e.target.value)}
                    className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-700 text-xs text-white focus:outline-none focus:border-emerald-500 transition"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">
                    Email Log Tab Name
                  </label>
                  <input
                    type="text"
                    value={emailTab}
                    onChange={(e) => setEmailTab(e.target.value)}
                    className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-700 text-xs text-white focus:outline-none focus:border-emerald-500 transition"
                  />
                </div>
              </div>

              {/* Auto Create Headers Checkbox */}
              <label className="flex items-center gap-2.5 p-3 rounded-xl bg-slate-950/60 border border-slate-800 cursor-pointer">
                <input
                  type="checkbox"
                  checked={autoHeaders}
                  onChange={(e) => setAutoHeaders(e.target.checked)}
                  className="rounded border-slate-700 text-emerald-500 focus:ring-emerald-500 bg-slate-900"
                />
                <div className="text-xs">
                  <span className="font-semibold text-slate-200">Automatically bootstrap headers</span>
                  <p className="text-slate-400 text-[11px]">
                    Creates formatted header rows for timestamps, caller info, transcript intent, satisfaction & turn metrics if not present.
                  </p>
                </div>
              </label>

              {/* Modal Buttons */}
              <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setModalOpen(false)}
                  className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-medium text-slate-300 transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-xs font-bold text-white shadow-lg transition active:scale-[0.98] disabled:opacity-50"
                >
                  {isSubmitting ? (
                    <>
                      <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                      Verifying Access...
                    </>
                  ) : (
                    <>
                      <Check className="w-3.5 h-3.5" />
                      Verify & Connect Sheet
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
