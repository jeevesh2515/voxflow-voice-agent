"use client";

import { useEffect, useState, type FormEvent } from "react";
import useSWR from "swr";
import {
  Bot,
  Briefcase,
  CheckCircle2,
  Clock,
  Globe,
  HeartHandshake,
  Lock,
  MessageSquare,
  PhoneForwarded,
  RefreshCw,
  Save,
  ShieldAlert,
  Sparkles,
  Zap,
} from "lucide-react";
import { api } from "@/lib/api";
import { useTenant } from "@/lib/tenant-context";
import type {
  AgentSettings as AgentSettingsResponse,
  AgentSettingsUpdateInput,
  FallbackEscalationMode,
  VoicePersona,
} from "@/lib/types";

const PERSONAS: ReadonlyArray<{
  value: VoicePersona;
  label: string;
  badge: string;
  icon: typeof Bot;
  description: string;
  sampleGreeting: string;
}> = [
  {
    value: "professional",
    label: "Professional",
    badge: "Polished & Courteous",
    icon: Briefcase,
    description: "Business-focused, respectful, and direct. Ideal for B2B supply-chain and corporate enterprise clients.",
    sampleGreeting: "Hello, this is Vaani from operations. How may I assist with your purchase order today?",
  },
  {
    value: "friendly",
    label: "Friendly",
    badge: "Warm & Empathetic",
    icon: HeartHandshake,
    description: "Conversational, approachable, and reassuring while keeping answers crisp and structured.",
    sampleGreeting: "Hi there! I'm Vaani. Let me quickly look up your shipment details for you right now.",
  },
  {
    value: "concise",
    label: "Concise",
    badge: "High-Efficiency & Brief",
    icon: Zap,
    description: "Ultra-brief, direct answers with zero fluff. Built for high-frequency warehouse dock dispatchers.",
    sampleGreeting: "Vaani here. Please provide your PO number or vendor name to check status.",
  },
  {
    value: "assertive",
    label: "Assertive",
    badge: "Structured & Authoritative",
    icon: ShieldAlert,
    description: "Strict procedural focus, identity compliance, and firm record verification.",
    sampleGreeting: "Welcome to dispatch. Before disclosing order details, please confirm your company and city.",
  },
];

const ESCALATION_MODES: ReadonlyArray<{
  value: FallbackEscalationMode;
  label: string;
  detail: string;
}> = [
  {
    value: "human_callback",
    label: "Human Callback",
    detail: "Reassures the caller that an operations specialist will call back at their verified contact number.",
  },
  {
    value: "transfer",
    label: "Live Phone Transfer",
    detail: "Initiates a live call transfer to your configured operations desk phone number.",
  },
  {
    value: "voicemail",
    label: "Dispatch Email Notification",
    detail: "Collects the caller's request and routes an urgent dispatch ticket to your operations inbox.",
  },
];

const TIMEZONES: ReadonlyArray<{ value: string; label: string }> = [
  { value: "Asia/Kolkata", label: "Asia/Kolkata (IST · UTC+5:30)" },
  { value: "Europe/London", label: "Europe/London (GMT/BST · UTC+0/+1)" },
  { value: "America/New_York", label: "America/New_York (EST/EDT · UTC-5/-4)" },
  { value: "America/Chicago", label: "America/Chicago (CST/CDT · UTC-6/-5)" },
  { value: "America/Los_Angeles", label: "America/Los_Angeles (PST/PDT · UTC-8/-7)" },
  { value: "UTC", label: "UTC (Coordinated Universal Time)" },
];

const WEEKDAYS = [
  { id: "mon", label: "Mon" },
  { id: "tue", label: "Tue" },
  { id: "wed", label: "Wed" },
  { id: "thu", label: "Thu" },
  { id: "fri", label: "Fri" },
  { id: "sat", label: "Sat" },
  { id: "sun", label: "Sun" },
];

export default function AgentSettings() {
  const { activeTenantId, activeTenant, demoMode } = useTenant();
  const canManage = Boolean(activeTenantId) && (demoMode || activeTenant.role === "owner");

  const { data, error, isLoading, mutate } = useSWR<AgentSettingsResponse>(
    activeTenantId ? ["agent-settings", activeTenantId] : null,
    () => api.agentSettings(activeTenantId),
    { revalidateOnFocus: true }
  );

  // Form state
  const [agentName, setAgentName] = useState("Vaani");
  const [voicePersona, setVoicePersona] = useState<VoicePersona>("professional");
  const [defaultLanguage, setDefaultLanguage] = useState<"en" | "hi">("en");
  const [welcomeMessage, setWelcomeMessage] = useState("");
  const [systemPromptOverride, setSystemPromptOverride] = useState("");
  const [businessHoursEnabled, setBusinessHoursEnabled] = useState(false);
  const [businessHoursStart, setBusinessHoursStart] = useState("09:00");
  const [businessHoursEnd, setBusinessHoursEnd] = useState("18:00");
  const [businessHoursTimezone, setBusinessHoursTimezone] = useState("Asia/Kolkata");
  const [selectedDays, setSelectedDays] = useState<string[]>(["mon", "tue", "wed", "thu", "fri"]);
  const [outOfHoursMessage, setOutOfHoursMessage] = useState("");
  const [fallbackMode, setFallbackMode] = useState<FallbackEscalationMode>("human_callback");
  const [fallbackPhone, setFallbackPhone] = useState("");
  const [fallbackEmail, setFallbackEmail] = useState("");
  const [maxVerificationFailures, setMaxVerificationFailures] = useState(3);

  const [saving, setSaving] = useState(false);
  const [feedback, setFeedback] = useState<{ type: "success" | "error"; text: string } | null>(null);

  // Sync form when SWR data loads or tenant switches
  useEffect(() => {
    if (data) {
      setAgentName(data.agent_name || "Vaani");
      setVoicePersona(data.voice_persona || "professional");
      setDefaultLanguage(data.default_language || "en");
      setWelcomeMessage(data.welcome_message || "");
      setSystemPromptOverride(data.system_prompt_override || "");
      setBusinessHoursEnabled(Boolean(data.business_hours_enabled));
      setBusinessHoursStart(data.business_hours_start || "09:00");
      setBusinessHoursEnd(data.business_hours_end || "18:00");
      setBusinessHoursTimezone(data.business_hours_timezone || "Asia/Kolkata");
      const days = data.business_days ? data.business_days.split(",").map((d) => d.trim().toLowerCase()) : ["mon", "tue", "wed", "thu", "fri"];
      setSelectedDays(days);
      setOutOfHoursMessage(data.out_of_hours_message || "");
      setFallbackMode(data.fallback_escalation_mode || "human_callback");
      setFallbackPhone(data.fallback_phone || "");
      setFallbackEmail(data.fallback_email || "");
      setMaxVerificationFailures(data.max_verification_failures || 3);
    }
  }, [data]);

  const toggleDay = (dayId: string) => {
    if (!canManage) return;
    setSelectedDays((prev) =>
      prev.includes(dayId) ? (prev.length > 1 ? prev.filter((d) => d !== dayId) : prev) : [...prev, dayId]
    );
  };

  const handleSave = async (e: FormEvent) => {
    e.preventDefault();
    if (!canManage) return;
    setSaving(true);
    setFeedback(null);

    const payload: AgentSettingsUpdateInput = {
      agent_name: agentName.trim(),
      voice_persona: voicePersona,
      default_language: defaultLanguage,
      welcome_message: welcomeMessage.trim() || null,
      system_prompt_override: systemPromptOverride.trim() || null,
      business_hours_enabled: businessHoursEnabled,
      business_hours_start: businessHoursStart,
      business_hours_end: businessHoursEnd,
      business_hours_timezone: businessHoursTimezone,
      business_days: selectedDays.join(","),
      out_of_hours_message: outOfHoursMessage.trim() || null,
      fallback_escalation_mode: fallbackMode,
      fallback_phone: fallbackPhone.trim() || null,
      fallback_email: fallbackEmail.trim() || null,
      max_verification_failures: maxVerificationFailures,
    };

    try {
      const updated = await api.updateAgentSettings(activeTenantId, payload);
      await mutate(updated, false);
      setFeedback({
        type: "success",
        text: "Agent configuration updated successfully. Prompt cache invalidated and active for new calls.",
      });
    } catch (err: any) {
      setFeedback({
        type: "error",
        text: err?.message || "Failed to update agent settings.",
      });
    } finally {
      setSaving(false);
    }
  };

  const activePersonaObj = PERSONAS.find((p) => p.value === voicePersona) || PERSONAS[0];

  return (
    <div className="space-y-6">
      <header className="overflow-hidden rounded-2xl border border-[#302840]/60 bg-[#141422]/60 shadow-xl backdrop-blur-xl">
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-[#302840]/40 bg-[#0f0f1a]/80 px-5 py-4 sm:px-6">
          <div className="flex items-center gap-3">
            <div className="rounded-xl border border-[#00ffcc]/30 bg-[#00ffcc]/10 p-2.5 text-[#00ffcc]">
              <Bot size={20} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-bold text-white">Voice Agent & Persona Settings</h2>
                <span className="rounded-full border border-[#00ffcc]/30 bg-[#00ffcc]/10 px-2 py-0.5 text-[10px] font-semibold text-[#00ffcc]">
                  Day 47
                </span>
              </div>
              <p className="text-xs text-[#a098b0]">
                Configure agent identity, persona demeanor, business hours, and fallback escalation policy.
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => mutate()}
            disabled={isLoading}
            className="flex items-center gap-1.5 rounded-lg border border-[#302840] bg-[#1e1e30] px-3 py-1.5 text-xs font-medium text-[#e8e0f0] transition hover:border-[#00ffcc]/40 hover:text-white"
          >
            <RefreshCw size={13} className={isLoading ? "animate-spin text-[#00ffcc]" : ""} />
            Refresh
          </button>
        </div>

        {!canManage && (
          <div className="flex items-center gap-2 border-b border-amber-500/20 bg-amber-500/10 px-5 py-2.5 text-xs text-amber-300 sm:px-6">
            <Lock size={14} className="shrink-0" />
            <span>Read-only view. Workspace owners alone can update agent persona and operating policies.</span>
          </div>
        )}

        {feedback && (
          <div
            className={`flex items-center gap-2.5 border-b px-5 py-3 text-xs sm:px-6 ${
              feedback.type === "success"
                ? "border-[#00ffcc]/30 bg-[#00ffcc]/10 text-[#00ffcc]"
                : "border-red-500/30 bg-red-500/10 text-red-300"
            }`}
          >
            {feedback.type === "success" ? <CheckCircle2 size={16} /> : <ShieldAlert size={16} />}
            <span>{feedback.text}</span>
          </div>
        )}

        {error && (
          <div className="border-b border-red-500/20 bg-red-500/10 px-5 py-3 text-xs text-red-300 sm:px-6">
            Failed to load agent settings: {error.message || "Unknown error"}
          </div>
        )}

        <form onSubmit={handleSave} className="p-5 sm:p-6 space-y-8">
          {/* Section 1: Voice Persona & Demeanor */}
          <section className="space-y-4">
            <div className="flex items-center gap-2">
              <Sparkles size={16} className="text-[#00ffcc]" />
              <h3 className="text-sm font-bold text-[#e8e0f0] uppercase tracking-wider">Voice Persona & Demeanor</h3>
            </div>
            <p className="text-xs text-[#a098b0]">
              Select the conversational style and demeanor injected into the system prompt for all inbound supplier calls.
            </p>

            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {PERSONAS.map((p) => {
                const isSelected = voicePersona === p.value;
                const IconComponent = p.icon;
                return (
                  <button
                    key={p.value}
                    type="button"
                    disabled={!canManage}
                    onClick={() => setVoicePersona(p.value)}
                    className={`relative flex flex-col justify-between rounded-xl border p-4 text-left transition-all ${
                      isSelected
                        ? "border-[#00ffcc] bg-[#00ffcc]/10 shadow-lg shadow-[#00ffcc]/5 ring-1 ring-[#00ffcc]"
                        : "border-[#302840] bg-[#1a1a2e]/60 hover:border-[#00ffcc]/30 hover:bg-[#1a1a2e]"
                    }`}
                  >
                    <div>
                      <div className="flex items-center justify-between gap-2">
                        <div className={`rounded-lg p-2 ${isSelected ? "bg-[#00ffcc]/20 text-[#00ffcc]" : "bg-[#252538] text-[#a098b0]"}`}>
                          <IconComponent size={18} />
                        </div>
                        {isSelected && (
                          <span className="flex h-2 w-2 rounded-full bg-[#00ffcc] shadow-[0_0_8px_#00ffcc]" />
                        )}
                      </div>
                      <h4 className="mt-3 text-sm font-bold text-white">{p.label}</h4>
                      <p className="mt-0.5 text-[10px] font-mono text-[#00ffcc]">{p.badge}</p>
                      <p className="mt-2 text-xs leading-5 text-[#a098b0]">{p.description}</p>
                    </div>
                  </button>
                );
              })}
            </div>
          </section>

          {/* Section 2: Agent Identity & Language */}
          <section className="space-y-4">
            <div className="flex items-center gap-2">
              <Globe size={16} className="text-[#ff2d78]" />
              <h3 className="text-sm font-bold text-[#e8e0f0] uppercase tracking-wider">Identity & Language</h3>
            </div>

            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              <div>
                <label className="block text-xs font-semibold text-[#e8e0f0]">Agent Name</label>
                <input
                  type="text"
                  disabled={!canManage}
                  value={agentName}
                  onChange={(e) => setAgentName(e.target.value)}
                  placeholder="e.g. Vaani, Atlas, Arya"
                  className="mt-1.5 w-full rounded-xl border border-[#302840] bg-[#1a1a2e] px-3.5 py-2.5 text-xs text-white placeholder-[#605870] transition focus:border-[#00ffcc] focus:outline-none"
                  required
                />
                <p className="mt-1 text-[10px] text-[#807890]">Name spoken aloud in greetings and self-introductions.</p>
              </div>

              <div>
                <label className="block text-xs font-semibold text-[#e8e0f0]">Default Language</label>
                <div className="mt-1.5 flex gap">
                  <button
                    type="button"
                    disabled={!canManage}
                    onClick={() => setDefaultLanguage("en")}
                    className="flex-1 rounded-xl border py-2.5 text-xs font-medium transition border-[#ff2d78] bg-[#ff2d78]/10 text-[#ff8db5]"
                  >
                    English (UK / Global)
                  </button>
                </div>
                <p className="mt-1 text-[10px] text-[#807890]">Primary English dialect for voice operations.</p>
              </div>

              <div className="sm:col-span-2 lg:col-span-1">
                <label className="block text-xs font-semibold text-[#e8e0f0]">Custom Welcome Message (Optional)</label>
                <input
                  type="text"
                  disabled={!canManage}
                  value={welcomeMessage}
                  onChange={(e) => setWelcomeMessage(e.target.value)}
                  placeholder="e.g. Welcome to Apex Logistics dock support."
                  className="mt-1.5 w-full rounded-xl border border-[#302840] bg-[#1a1a2e] px-3.5 py-2.5 text-xs text-white placeholder-[#605870] transition focus:border-[#00ffcc] focus:outline-none"
                />
                <p className="mt-1 text-[10px] text-[#807890]">Optional opening line spoken before intent gathering.</p>
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-[#e8e0f0]">Company Guidelines & Custom Instructions</label>
              <textarea
                disabled={!canManage}
                rows={3}
                value={systemPromptOverride}
                onChange={(e) => setSystemPromptOverride(e.target.value)}
                placeholder="e.g. For pallet deliveries exceeding 200 units, confirm that the driver has a tail-lift vehicle. Do not accept returns on refrigerated milk."
                className="mt-1.5 w-full rounded-xl border border-[#302840] bg-[#1a1a2e] p-3 text-xs text-white placeholder-[#605870] transition focus:border-[#00ffcc] focus:outline-none leading-relaxed"
              />
              <p className="mt-1 text-[10px] text-[#807890]">
                Appended under # Company Specific Guidelines in the agent&apos;s system prompt.
              </p>
            </div>
          </section>

          {/* Section 3: Operating / Business Hours */}
          <section className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Clock size={16} className="text-[#00ffcc]" />
                <h3 className="text-sm font-bold text-[#e8e0f0] uppercase tracking-wider">Business Operating Hours</h3>
              </div>
              <label className="flex items-center gap-2.5 cursor-pointer">
                <input
                  type="checkbox"
                  disabled={!canManage}
                  checked={businessHoursEnabled}
                  onChange={(e) => setBusinessHoursEnabled(e.target.checked)}
                  className="h-4 w-4 rounded border-[#302840] bg-[#1a1a2e] text-[#00ffcc] focus:ring-[#00ffcc]"
                />
                <span className="text-xs font-medium text-[#e8e0f0]">Enable Business Hours Awareness</span>
              </label>
            </div>

            {businessHoursEnabled && (
              <div className="rounded-xl border border-[#302840]/60 bg-[#161628] p-4 space-y-4">
                <div className="grid gap-4 sm:grid-cols-3">
                  <div>
                    <label className="block text-xs font-semibold text-[#e8e0f0]">Opening Time (HH:MM)</label>
                    <input
                      type="text"
                      disabled={!canManage}
                      value={businessHoursStart}
                      onChange={(e) => setBusinessHoursStart(e.target.value)}
                      placeholder="09:00"
                      className="mt-1.5 w-full rounded-xl border border-[#302840] bg-[#1a1a2e] px-3.5 py-2 text-xs text-white placeholder-[#605870] focus:border-[#00ffcc] focus:outline-none"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-[#e8e0f0]">Closing Time (HH:MM)</label>
                    <input
                      type="text"
                      disabled={!canManage}
                      value={businessHoursEnd}
                      onChange={(e) => setBusinessHoursEnd(e.target.value)}
                      placeholder="18:00"
                      className="mt-1.5 w-full rounded-xl border border-[#302840] bg-[#1a1a2e] px-3.5 py-2 text-xs text-white placeholder-[#605870] focus:border-[#00ffcc] focus:outline-none"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-[#e8e0f0]">Timezone</label>
                    <select
                      disabled={!canManage}
                      value={businessHoursTimezone}
                      onChange={(e) => setBusinessHoursTimezone(e.target.value)}
                      className="mt-1.5 w-full rounded-xl border border-[#302840] bg-[#1a1a2e] px-3 py-2 text-xs text-white focus:border-[#00ffcc] focus:outline-none"
                    >
                      {TIMEZONES.map((tz) => (
                        <option key={tz.value} value={tz.value} className="bg-[#141422]">
                          {tz.label}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-[#e8e0f0]">Operating Days</label>
                  <div className="mt-1.5 flex flex-wrap gap-2">
                    {WEEKDAYS.map((w) => {
                      const active = selectedDays.includes(w.id);
                      return (
                        <button
                          key={w.id}
                          type="button"
                          disabled={!canManage}
                          onClick={() => toggleDay(w.id)}
                          className={`rounded-lg border px-3 py-1.5 text-xs font-semibold transition ${
                            active
                              ? "border-[#00ffcc] bg-[#00ffcc]/15 text-[#00ffcc]"
                              : "border-[#302840] bg-[#1a1a2e] text-[#605870] hover:text-white"
                          }`}
                        >
                          {w.label}
                        </button>
                      );
                    })}
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-[#e8e0f0]">Out of Hours Spoken Advisory</label>
                  <input
                    type="text"
                    disabled={!canManage}
                    value={outOfHoursMessage}
                    onChange={(e) => setOutOfHoursMessage(e.target.value)}
                    placeholder="e.g. Our loading docks operate 9 AM to 6 PM. Out-of-hours deliveries require advance booking."
                    className="mt-1.5 w-full rounded-xl border border-[#302840] bg-[#1a1a2e] px-3.5 py-2 text-xs text-white placeholder-[#605870] focus:border-[#00ffcc] focus:outline-none"
                  />
                  <p className="mt-1 text-[10px] text-[#807890]">Instructions conveyed by the agent when receiving calls after hours.</p>
                </div>
              </div>
            )}
          </section>

          {/* Section 4: Fallback & Escalation Policy */}
          <section className="space-y-4">
            <div className="flex items-center gap-2">
              <PhoneForwarded size={16} className="text-[#ff8db5]" />
              <h3 className="text-sm font-bold text-[#e8e0f0] uppercase tracking-wider">Fallback & Escalation Policy</h3>
            </div>

            <div className="grid gap-3 sm:grid-cols-3">
              {ESCALATION_MODES.map((mode) => {
                const isSelected = fallbackMode === mode.value;
                return (
                  <button
                    key={mode.value}
                    type="button"
                    disabled={!canManage}
                    onClick={() => setFallbackMode(mode.value)}
                    className={`rounded-xl border p-4 text-left transition ${
                      isSelected
                        ? "border-[#ff2d78] bg-[#ff2d78]/10 ring-1 ring-[#ff2d78]"
                        : "border-[#302840] bg-[#1a1a2e]/60 hover:border-[#ff2d78]/30 hover:bg-[#1a1a2e]"
                    }`}
                  >
                    <h4 className="text-xs font-bold text-white">{mode.label}</h4>
                    <p className="mt-1 text-[11px] leading-4 text-[#a098b0]">{mode.detail}</p>
                  </button>
                );
              })}
            </div>

            <div className="grid gap-4 sm:grid-cols-3">
              {fallbackMode === "transfer" && (
                <div>
                  <label className="block text-xs font-semibold text-[#e8e0f0]">Transfer Destination Phone (E.164)</label>
                  <input
                    type="text"
                    disabled={!canManage}
                    value={fallbackPhone}
                    onChange={(e) => setFallbackPhone(e.target.value)}
                    placeholder="+442079460991"
                    className="mt-1.5 w-full rounded-xl border border-[#302840] bg-[#1a1a2e] px-3.5 py-2 text-xs text-white placeholder-[#605870] focus:border-[#ff2d78] focus:outline-none"
                  />
                </div>
              )}

              {fallbackMode === "voicemail" && (
                <div>
                  <label className="block text-xs font-semibold text-[#e8e0f0]">Operations Dispatch Email</label>
                  <input
                    type="email"
                    disabled={!canManage}
                    value={fallbackEmail}
                    onChange={(e) => setFallbackEmail(e.target.value)}
                    placeholder="dispatch@company.com"
                    className="mt-1.5 w-full rounded-xl border border-[#302840] bg-[#1a1a2e] px-3.5 py-2 text-xs text-white placeholder-[#605870] focus:border-[#ff2d78] focus:outline-none"
                  />
                </div>
              )}

              <div>
                <label className="block text-xs font-semibold text-[#e8e0f0]">
                  Max Verification Attempts: {maxVerificationFailures}
                </label>
                <input
                  type="range"
                  min={1}
                  max={5}
                  disabled={!canManage}
                  value={maxVerificationFailures}
                  onChange={(e) => setMaxVerificationFailures(parseInt(e.target.value, 10))}
                  className="mt-2.5 w-full accent-[#00ffcc]"
                />
                <div className="flex justify-between text-[10px] text-[#605870]">
                  <span>1 (Strict)</span>
                  <span>3 (Default)</span>
                  <span>5 (Relaxed)</span>
                </div>
              </div>
            </div>
          </section>

          {/* Section 5: Live Persona Preview Card */}
          <section className="rounded-xl border border-[#302840]/60 bg-[#0f0f1a]/90 p-4 space-y-3">
            <div className="flex items-center justify-between text-xs text-[#a098b0]">
              <span className="font-semibold text-[#e8e0f0] flex items-center gap-1.5">
                <MessageSquare size={14} className="text-[#00ffcc]" />
                Live Agent Persona Preview
              </span>
              <span className="font-mono text-[10px] text-[#00ffcc]">
                Active Style: {activePersonaObj.label} (English)
              </span>
            </div>
            <div className="rounded-lg border border-[#252538] bg-[#141422] p-3.5">
              <p className="text-xs font-medium text-white italic">
                &ldquo;{welcomeMessage || activePersonaObj.sampleGreeting}&rdquo;
              </p>
              <div className="mt-2 flex flex-wrap gap-2 text-[10px]">
                <span className="rounded bg-[#00ffcc]/10 px-2 py-0.5 font-mono text-[#00ffcc]">
                  Agent: {agentName || "Vaani"}
                </span>
                <span className="rounded bg-[#ff2d78]/10 px-2 py-0.5 font-mono text-[#ff8db5]">
                  Escalation: {fallbackMode}
                </span>
                {businessHoursEnabled && (
                  <span className="rounded bg-emerald-500/10 px-2 py-0.5 font-mono text-emerald-300">
                    Hours: {businessHoursStart}-{businessHoursEnd} ({selectedDays.join(",")})
                  </span>
                )}
              </div>
            </div>
          </section>

          {/* Submit Button */}
          {canManage && (
            <div className="flex justify-end pt-2">
              <button
                type="submit"
                disabled={saving}
                className="flex items-center gap-2 rounded-xl bg-gradient-to-r from-[#00ffcc] to-[#00b894] px-6 py-2.5 text-xs font-bold text-[#0a0a14] shadow-lg shadow-[#00ffcc]/20 transition hover:brightness-110 focus:outline-none disabled:opacity-50"
              >
                {saving ? <RefreshCw size={14} className="animate-spin" /> : <Save size={14} />}
                {saving ? "Saving Changes..." : "Save Agent Configuration"}
              </button>
            </div>
          )}
        </form>
      </header>
    </div>
  );
}
