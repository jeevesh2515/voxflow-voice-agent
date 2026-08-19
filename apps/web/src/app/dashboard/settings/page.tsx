"use client";

import { useState, useEffect } from "react";
import useSWR, { mutate } from "swr";
import {
  Sliders,
  Bot,
  Globe,
  Webhook,
  Phone,
  Save,
  CheckCircle2,
  AlertCircle,
  KeyRound,
  Crown,
  Sparkles,
  Shield,
  Activity,
} from "lucide-react";
import { api } from "@/lib/api";
import { useTenant } from "@/lib/tenant-context";

export default function SettingsPage() {
  const { activeTenantId, activeTenant } = useTenant();
  const { data: tenantData, error, isLoading } = useSWR(
    ["tenant-details", activeTenantId],
    () => api.getTenant(activeTenantId),
  );

  // Form states
  const [companyName, setCompanyName] = useState("");
  const [agentName, setAgentName] = useState("Vaani");
  const [defaultLanguage, setDefaultLanguage] = useState("hi");
  const [systemPrompt, setSystemPrompt] = useState("");
  const [welcomeMessage, setWelcomeMessage] = useState("");
  const [webhookUrl, setWebhookUrl] = useState("");
  const [webhookSecret, setWebhookSecret] = useState("");
  const [phoneNumber, setPhoneNumber] = useState("");
  const [phoneLabel, setPhoneLabel] = useState("");

  const [saving, setSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [saveError, setSaveError] = useState("");

  const [phoneSaving, setPhoneSaving] = useState(false);
  const [phoneSuccess, setPhoneSuccess] = useState(false);
  const [phoneError, setPhoneError] = useState("");

  useEffect(() => {
    if (tenantData) {
      setCompanyName(tenantData.name || activeTenant.name || "");
      setAgentName(tenantData.agent_name || "Vaani");
      setDefaultLanguage(tenantData.default_language || "hi");
      setSystemPrompt(tenantData.system_prompt_override || "");
      setWelcomeMessage(tenantData.welcome_message || "");
      setWebhookUrl(tenantData.webhook_url || "");
    }
  }, [tenantData, activeTenant]);

  const handleSaveSettings = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setSaveSuccess(false);
    setSaveError("");

    try {
      await api.updateTenant(activeTenantId, {
        name: companyName.trim() || undefined,
        agent_name: agentName.trim() || undefined,
        default_language: defaultLanguage,
        system_prompt_override: systemPrompt.trim() || null,
        welcome_message: welcomeMessage.trim() || null,
        webhook_url: webhookUrl.trim() || null,
        webhook_secret: webhookSecret.trim() || undefined,
      });
      mutate(["tenant-details", activeTenantId]);
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 4000);
    } catch (err: any) {
      setSaveError(err.message || "Failed to update settings");
    } finally {
      setSaving(false);
    }
  };

  const handleMapPhone = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!phoneNumber.trim()) return;
    setPhoneSaving(true);
    setPhoneSuccess(false);
    setPhoneError("");

    try {
      await api.mapPhone(activeTenantId, phoneNumber.trim(), phoneLabel.trim());
      setPhoneSuccess(true);
      setTimeout(() => setPhoneSuccess(false), 4000);
    } catch (err: any) {
      setPhoneError(err.message || "Failed to map phone number");
    } finally {
      setPhoneSaving(false);
    }
  };

  return (
    <div className="space-y-6 max-w-5xl mx-auto pb-16">
      {/* ==================== PAGE HEADER ==================== */}
      <header className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 bg-[#12121e] p-6 rounded-2xl border border-[#242436] shadow-sm">
        <div className="space-y-1">
          <div className="flex items-center gap-2 text-xs font-mono text-[#94a3b8]">
            <span>Configuration</span>
            <span>/</span>
            <span className="text-[#00ffcc] font-bold">{activeTenant.name}</span>
          </div>
          <h1 className="text-xl sm:text-2xl font-headline font-bold text-white tracking-tight">
            AI Agent & Telephony Settings
          </h1>
          <p className="text-xs sm:text-sm text-[#94a3b8]">
            Custom persona prompts, Twilio telephone mapping, multi-lingual TTS voice models, and outbound webhooks.
          </p>
        </div>
      </header>

      {/* ==================== FORM ==================== */}
      <form onSubmit={handleSaveSettings} className="space-y-6">
        {/* Section 1: Tenant & Voice Persona */}
        <div className="bg-[#141422] p-6 sm:p-8 rounded-2xl border border-[#28283c] shadow-sm space-y-5">
          <div className="flex items-center gap-3 pb-3 border-b border-[#242436]">
            <div className="w-10 h-10 rounded-xl bg-[#ff2d78]/15 border border-[#ff2d78]/30 flex items-center justify-center text-[#ff2d78]">
              <Bot size={20} />
            </div>
            <div>
              <h2 className="font-headline font-bold text-base text-white">Voice Agent Persona</h2>
              <p className="text-xs text-[#94a3b8]">Configure agent personality, name, and default language</p>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="text-[11px] font-mono uppercase tracking-wider text-[#94a3b8] block mb-1.5 font-bold">
                Company Display Name
              </label>
              <input
                type="text"
                value={companyName}
                onChange={(e) => setCompanyName(e.target.value)}
                placeholder="e.g. Varun Beverages"
                className="w-full px-3.5 py-2 rounded-xl bg-[#10101a] border border-[#28283c] text-xs text-white focus:border-[#ff2d78] focus:outline-none"
              />
            </div>

            <div>
              <label className="text-[11px] font-mono uppercase tracking-wider text-[#94a3b8] block mb-1.5 font-bold">
                AI Agent Persona Name
              </label>
              <input
                type="text"
                value={agentName}
                onChange={(e) => setAgentName(e.target.value)}
                placeholder="Vaani"
                className="w-full px-3.5 py-2 rounded-xl bg-[#10101a] border border-[#28283c] text-xs text-[#00ffcc] font-bold focus:border-[#ff2d78] focus:outline-none"
              />
            </div>

            <div>
              <label className="text-[11px] font-mono uppercase tracking-wider text-[#94a3b8] block mb-1.5 font-bold">
                Default Voice & Language
              </label>
              <select
                value={defaultLanguage}
                onChange={(e) => setDefaultLanguage(e.target.value)}
                className="w-full px-3.5 py-2 rounded-xl bg-[#10101a] border border-[#28283c] text-xs text-white focus:border-[#ff2d78] focus:outline-none"
              >
                <option value="hi">Hindi (hi-IN-SwaraNeural)</option>
                <option value="en">English (en-IN-NeerjaNeural)</option>
              </select>
            </div>
          </div>

          <div>
            <label className="text-[11px] font-mono uppercase tracking-wider text-[#94a3b8] block mb-1.5 font-bold">
              Custom Welcome / Greeting Message
            </label>
            <input
              type="text"
              value={welcomeMessage}
              onChange={(e) => setWelcomeMessage(e.target.value)}
              placeholder="नमस्ते, Varun Beverages में आपका स्वागत है। मैं वाणी हूँ, मैं आपकी क्या सहायता कर सकती हूँ?"
              className="w-full px-3.5 py-2 rounded-xl bg-[#10101a] border border-[#28283c] text-xs text-white focus:border-[#ff2d78] focus:outline-none"
            />
          </div>
        </div>

        {/* Section 2: Custom System Prompt Instructions */}
        <div className="bg-[#141422] p-6 sm:p-8 rounded-2xl border border-[#28283c] shadow-sm space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-[#242436]">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-[#00ffcc]/15 border border-[#00ffcc]/30 flex items-center justify-center text-[#00ffcc]">
                <Sparkles size={20} />
              </div>
              <div>
                <h2 className="font-headline font-bold text-base text-white">Prompt & Business Logic Engine</h2>
                <p className="text-xs text-[#94a3b8]">Custom instructions merged into the LLM system prompt for {activeTenant.name}</p>
              </div>
            </div>
          </div>

          <div>
            <label className="text-[11px] font-mono uppercase tracking-wider text-[#94a3b8] block mb-1.5 font-bold">
              Custom Business Guidelines / Fallback Instructions
            </label>
            <textarea
              rows={5}
              value={systemPrompt}
              onChange={(e) => setSystemPrompt(e.target.value)}
              placeholder={`# Custom rules for ${activeTenant.name}:
- Always ask for 2FA PIN before confirming any purchase orders.
- If caller asks for warehouse delivery timings, mention 9 AM to 6 PM IST.
- For emergency stock issues, offer to escalate directly to the plant manager.`}
              className="w-full p-4 rounded-xl bg-[#10101a] border border-[#28283c] text-xs text-white focus:border-[#00ffcc] focus:outline-none font-mono leading-relaxed"
            />
            <p className="text-[11px] text-[#64748b] mt-1.5">
              Leave blank to use VoxFlow default supply-chain logistics system prompt.
            </p>
          </div>
        </div>

        {/* Section 3: Outbound ERP Webhooks */}
        <div className="bg-[#141422] p-6 sm:p-8 rounded-2xl border border-[#28283c] shadow-sm space-y-4">
          <div className="flex items-center gap-3 pb-3 border-b border-[#242436]">
            <div className="w-10 h-10 rounded-xl bg-purple-500/15 border border-purple-500/30 flex items-center justify-center text-purple-400">
              <Webhook size={20} />
            </div>
            <div>
              <h2 className="font-headline font-bold text-base text-white">Outbound Webhooks (ERP / CRM)</h2>
              <p className="text-xs text-[#94a3b8]">
                Dispatches HMAC-signed JSON events on order_created, appointment_booked, and call_escalated
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="text-[11px] font-mono uppercase tracking-wider text-[#94a3b8] block mb-1.5 font-bold">
                Webhook Destination URL
              </label>
              <input
                type="url"
                value={webhookUrl}
                onChange={(e) => setWebhookUrl(e.target.value)}
                placeholder="https://api.yourcompany.com/voxflow/webhook"
                className="w-full px-3.5 py-2 rounded-xl bg-[#10101a] border border-[#28283c] text-xs text-white focus:border-purple-400 focus:outline-none font-mono"
              />
            </div>
            <div>
              <label className="text-[11px] font-mono uppercase tracking-wider text-[#94a3b8] block mb-1.5 font-bold">
                Webhook HMAC Secret Key
              </label>
              <input
                type="password"
                value={webhookSecret}
                onChange={(e) => setWebhookSecret(e.target.value)}
                placeholder="whsec_••••••••••••••••"
                className="w-full px-3.5 py-2 rounded-xl bg-[#10101a] border border-[#28283c] text-xs text-white focus:border-purple-400 focus:outline-none font-mono"
              />
            </div>
          </div>
        </div>

        {/* Status / Save Buttons */}
        {saveSuccess && (
          <div className="flex items-center gap-2 text-xs text-[#00ffcc] bg-[#00ffcc]/10 border border-[#00ffcc]/30 p-3 rounded-xl">
            <CheckCircle2 size={16} /> Settings and AI agent persona updated successfully!
          </div>
        )}

        {saveError && (
          <div className="flex items-center gap-2 text-xs text-red-400 bg-red-500/10 border border-red-500/30 p-3 rounded-xl">
            <AlertCircle size={16} /> {saveError}
          </div>
        )}

        <div className="flex justify-end">
          <button
            type="submit"
            disabled={saving}
            className="px-6 py-2.5 rounded-xl bg-[#ff2d78] hover:bg-[#e02669] text-white text-xs font-bold transition-colors flex items-center gap-2 shadow-sm disabled:opacity-50"
          >
            <Save size={15} />
            <span>{saving ? "Saving Changes..." : "Save Agent Configuration"}</span>
          </button>
        </div>
      </form>

      {/* ==================== PHONE NUMBER MAPPING ==================== */}
      <div className="bg-[#141422] p-6 sm:p-8 rounded-2xl border border-[#28283c] shadow-sm space-y-5">
        <div className="flex items-center gap-3 pb-3 border-b border-[#242436]">
          <div className="w-10 h-10 rounded-xl bg-amber-500/15 border border-amber-500/30 flex items-center justify-center text-amber-400">
            <Phone size={20} />
          </div>
          <div>
            <h2 className="font-headline font-bold text-base text-white">Twilio Telephony Mapping</h2>
            <p className="text-xs text-[#94a3b8]">Route incoming telephone numbers directly to {activeTenant.name}</p>
          </div>
        </div>

        <form onSubmit={handleMapPhone} className="grid grid-cols-1 sm:grid-cols-3 gap-3 items-end">
          <div>
            <label className="text-[11px] font-mono uppercase tracking-wider text-[#94a3b8] block mb-1.5 font-bold">
              Inbound Phone Number (E.164)
            </label>
            <input
              type="text"
              required
              value={phoneNumber}
              onChange={(e) => setPhoneNumber(e.target.value)}
              placeholder="+14155550199"
              className="w-full px-3.5 py-2 rounded-xl bg-[#10101a] border border-[#28283c] text-xs text-white focus:border-amber-400 focus:outline-none font-mono"
            />
          </div>

          <div>
            <label className="text-[11px] font-mono uppercase tracking-wider text-[#94a3b8] block mb-1.5 font-bold">
              Line Label / Description
            </label>
            <input
              type="text"
              value={phoneLabel}
              onChange={(e) => setPhoneLabel(e.target.value)}
              placeholder="e.g. North Region Supplier Desk"
              className="w-full px-3.5 py-2 rounded-xl bg-[#10101a] border border-[#28283c] text-xs text-white focus:border-amber-400 focus:outline-none"
            />
          </div>

          <div>
            <button
              type="submit"
              disabled={phoneSaving}
              className="w-full py-2.5 rounded-xl bg-amber-500 hover:bg-amber-400 text-black text-xs font-bold transition-colors shadow-sm disabled:opacity-50"
            >
              {phoneSaving ? "Mapping..." : "Assign Phone Line"}
            </button>
          </div>
        </form>

        {phoneSuccess && (
          <div className="flex items-center gap-2 text-xs text-[#00ffcc] bg-[#00ffcc]/10 border border-[#00ffcc]/30 p-3 rounded-xl">
            <CheckCircle2 size={16} /> Phone number mapped to {activeTenant.name} successfully!
          </div>
        )}

        {phoneError && (
          <div className="flex items-center gap-2 text-xs text-red-400 bg-red-500/10 border border-red-500/30 p-3 rounded-xl">
            <AlertCircle size={16} /> {phoneError}
          </div>
        )}
      </div>
    </div>
  );
}
