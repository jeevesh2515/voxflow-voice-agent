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
      <header>
        <div className="flex items-center gap-2 text-xs font-label uppercase tracking-widest text-[#a098b0] mb-1">
          <span>Configuration</span>
          <span>/</span>
          <span className="text-[#00ffcc] font-bold">{activeTenant.name}</span>
        </div>
        <h1 className="text-2xl sm:text-3xl font-headline font-extrabold text-[#e8e0f0] tracking-[0.05em] uppercase">
          AI Agent & <span className="text-[#ff2d78] text-glow-primary">Settings</span>
        </h1>
        <p className="text-[#a098b0] font-body text-sm mt-1">
          Custom persona prompts, Twilio telephone mapping, multi-lingual TTS voice models, and outbound webhooks.
        </p>
      </header>

      {/* ==================== FORM ==================== */}
      <form onSubmit={handleSaveSettings} className="space-y-6">
        {/* Section 1: Tenant & Voice Persona */}
        <div className="glass-panel p-6 sm:p-8 rounded-2xl border border-[#302840]/60 space-y-5">
          <div className="flex items-center gap-3 pb-3 border-b border-[#302840]/40">
            <div className="w-10 h-10 rounded-xl bg-[#ff2d78]/10 border border-[#ff2d78]/30 flex items-center justify-center text-[#ff2d78]">
              <Bot size={20} />
            </div>
            <div>
              <h2 className="font-headline font-bold text-base text-[#e8e0f0]">Voice Agent Persona</h2>
              <p className="text-xs text-[#a098b0]">Configure agent personality, name, and default language</p>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="text-[10px] font-label uppercase tracking-widest text-[#e8e0f0] block mb-1.5">
                Company Display Name
              </label>
              <input
                type="text"
                value={companyName}
                onChange={(e) => setCompanyName(e.target.value)}
                placeholder="e.g. Varun Beverages"
                className="w-full px-3.5 py-2.5 rounded-xl bg-[#181824] border border-[#302840] text-xs text-[#e8e0f0] focus:border-[#ff2d78] focus:outline-none font-body"
              />
            </div>

            <div>
              <label className="text-[10px] font-label uppercase tracking-widest text-[#e8e0f0] block mb-1.5">
                AI Agent Name
              </label>
              <input
                type="text"
                value={agentName}
                onChange={(e) => setAgentName(e.target.value)}
                placeholder="Vaani"
                className="w-full px-3.5 py-2.5 rounded-xl bg-[#181824] border border-[#302840] text-xs text-[#00ffcc] font-headline font-bold focus:border-[#ff2d78] focus:outline-none"
              />
            </div>

            <div>
              <label className="text-[10px] font-label uppercase tracking-widest text-[#e8e0f0] block mb-1.5">
                Default Voice & Language
              </label>
              <select
                value={defaultLanguage}
                onChange={(e) => setDefaultLanguage(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-xl bg-[#181824] border border-[#302840] text-xs text-[#e8e0f0] focus:border-[#ff2d78] focus:outline-none"
              >
                <option value="hi">Hindi (hi-IN-SwaraNeural)</option>
                <option value="en">English (en-IN-NeerjaNeural)</option>
              </select>
            </div>
          </div>

          <div>
            <label className="text-[10px] font-label uppercase tracking-widest text-[#e8e0f0] block mb-1.5">
              Custom Welcome / Greeting Message
            </label>
            <input
              type="text"
              value={welcomeMessage}
              onChange={(e) => setWelcomeMessage(e.target.value)}
              placeholder="नमस्ते, Varun Beverages में आपका स्वागत है। मैं वाणी हूँ, मैं आपकी क्या सहायता कर सकती हूँ?"
              className="w-full px-3.5 py-2.5 rounded-xl bg-[#181824] border border-[#302840] text-xs text-[#e8e0f0] focus:border-[#ff2d78] focus:outline-none font-body"
            />
          </div>
        </div>

        {/* Section 2: Custom System Prompt Instructions */}
        <div className="glass-panel p-6 sm:p-8 rounded-2xl border border-[#302840]/60 space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-[#302840]/40">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-[#00ffcc]/10 border border-[#00ffcc]/30 flex items-center justify-center text-[#00ffcc]">
                <Sparkles size={20} />
              </div>
              <div>
                <h2 className="font-headline font-bold text-base text-[#e8e0f0]">Prompt & Business Logic Engine</h2>
                <p className="text-xs text-[#a098b0]">Custom instructions merged into the LLM system prompt for {activeTenant.name}</p>
              </div>
            </div>
          </div>

          <div>
            <label className="text-[10px] font-label uppercase tracking-widest text-[#e8e0f0] block mb-1.5">
              Custom Business Guidelines / Fallback Instructions
            </label>
            <textarea
              rows={6}
              value={systemPrompt}
              onChange={(e) => setSystemPrompt(e.target.value)}
              placeholder={`# Custom rules for ${activeTenant.name}:
- Always ask for 2FA PIN before confirming any purchase orders.
- If caller asks for warehouse delivery timings, mention 9 AM to 6 PM IST.
- For emergency stock issues, offer to escalate directly to the plant manager.`}
              className="w-full p-4 rounded-xl bg-[#181824] border border-[#302840] text-xs text-[#e8e0f0] focus:border-[#00ffcc] focus:outline-none font-mono leading-relaxed"
            />
            <p className="text-[11px] text-[#a098b0] mt-1.5">
              Leave blank to use VoxFlow default supply-chain logistics system prompt.
            </p>
          </div>
        </div>

        {/* Section 3: Outbound ERP Webhooks */}
        <div className="glass-panel p-6 sm:p-8 rounded-2xl border border-[#302840]/60 space-y-4">
          <div className="flex items-center gap-3 pb-3 border-b border-[#302840]/40">
            <div className="w-10 h-10 rounded-xl bg-purple-500/10 border border-purple-500/30 flex items-center justify-center text-purple-400">
              <Webhook size={20} />
            </div>
            <div>
              <h2 className="font-headline font-bold text-base text-[#e8e0f0]">Outbound Webhooks (ERP / CRM)</h2>
              <p className="text-xs text-[#a098b0]">
                Dispatches HMAC-signed JSON events on order_created, appointment_booked, and call_escalated
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="text-[10px] font-label uppercase tracking-widest text-[#e8e0f0] block mb-1.5">
                Webhook Destination URL
              </label>
              <input
                type="url"
                value={webhookUrl}
                onChange={(e) => setWebhookUrl(e.target.value)}
                placeholder="https://api.yourcompany.com/voxflow/webhook"
                className="w-full px-3.5 py-2.5 rounded-xl bg-[#181824] border border-[#302840] text-xs text-[#e8e0f0] focus:border-purple-400 focus:outline-none font-mono"
              />
            </div>
            <div>
              <label className="text-[10px] font-label uppercase tracking-widest text-[#e8e0f0] block mb-1.5">
                Webhook HMAC Secret Key
              </label>
              <input
                type="password"
                value={webhookSecret}
                onChange={(e) => setWebhookSecret(e.target.value)}
                placeholder="whsec_••••••••••••••••"
                className="w-full px-3.5 py-2.5 rounded-xl bg-[#181824] border border-[#302840] text-xs text-[#e8e0f0] focus:border-purple-400 focus:outline-none font-mono"
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
          <div className="flex items-center gap-2 text-xs text-[#ff2d78] bg-[#ff2d78]/10 border border-[#ff2d78]/30 p-3 rounded-xl">
            <AlertCircle size={16} /> {saveError}
          </div>
        )}

        <div className="flex justify-end">
          <button
            type="submit"
            disabled={saving}
            className="px-6 py-3 rounded-xl bg-[#ff2d78] text-[#1a0010] text-xs font-headline font-bold uppercase tracking-wider neon-glow-primary hover:scale-105 active:scale-95 transition-all flex items-center gap-2 disabled:opacity-50"
          >
            <Save size={15} /> {saving ? "Saving Changes..." : "Save Agent Configuration"}
          </button>
        </div>
      </form>

      {/* ==================== PHONE NUMBER MAPPING ==================== */}
      <div className="glass-panel p-6 sm:p-8 rounded-2xl border border-[#302840]/60 space-y-5">
        <div className="flex items-center gap-3 pb-3 border-b border-[#302840]/40">
          <div className="w-10 h-10 rounded-xl bg-[#ffe04a]/10 border border-[#ffe04a]/30 flex items-center justify-center text-[#ffe04a]">
            <Phone size={20} />
          </div>
          <div>
            <h2 className="font-headline font-bold text-base text-[#e8e0f0]">Twilio Telephony Mapping</h2>
            <p className="text-xs text-[#a098b0]">Route incoming telephone numbers directly to {activeTenant.name}</p>
          </div>
        </div>

        <form onSubmit={handleMapPhone} className="grid grid-cols-1 sm:grid-cols-3 gap-3 items-end">
          <div>
            <label className="text-[10px] font-label uppercase tracking-widest text-[#e8e0f0] block mb-1.5">
              Inbound Phone Number (E.164)
            </label>
            <input
              type="text"
              required
              value={phoneNumber}
              onChange={(e) => setPhoneNumber(e.target.value)}
              placeholder="+14155550199"
              className="w-full px-3.5 py-2.5 rounded-xl bg-[#181824] border border-[#302840] text-xs text-[#e8e0f0] focus:border-[#ffe04a] focus:outline-none font-mono"
            />
          </div>

          <div>
            <label className="text-[10px] font-label uppercase tracking-widest text-[#e8e0f0] block mb-1.5">
              Line Label / Description
            </label>
            <input
              type="text"
              value={phoneLabel}
              onChange={(e) => setPhoneLabel(e.target.value)}
              placeholder="e.g. North Region Supplier Desk"
              className="w-full px-3.5 py-2.5 rounded-xl bg-[#181824] border border-[#302840] text-xs text-[#e8e0f0] focus:border-[#ffe04a] focus:outline-none font-body"
            />
          </div>

          <div>
            <button
              type="submit"
              disabled={phoneSaving}
              className="w-full py-2.5 rounded-xl bg-[#ffe04a] text-[#1a0010] text-xs font-headline font-bold uppercase tracking-wider shadow-[0_0_15px_rgba(255,224,74,0.4)] hover:scale-105 active:scale-95 transition-all disabled:opacity-50"
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
          <div className="flex items-center gap-2 text-xs text-[#ff2d78] bg-[#ff2d78]/10 border border-[#ff2d78]/30 p-3 rounded-xl">
            <AlertCircle size={16} /> {phoneError}
          </div>
        )}
      </div>
    </div>
  );
}
