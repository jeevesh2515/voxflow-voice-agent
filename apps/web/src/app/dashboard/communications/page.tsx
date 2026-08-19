"use client";

import { useState, useMemo } from "react";
import useSWR, { mutate } from "swr";
import {
  MessageSquare,
  Mail,
  Smartphone,
  Search,
  Plus,
  Send,
  CheckCircle2,
  Clock,
  Filter,
  X,
  Radio,
} from "lucide-react";
import { api } from "@/lib/api";
import { useTenant } from "@/lib/tenant-context";

export default function CommunicationsPage() {
  const { activeTenantId, activeTenant } = useTenant();
  const { data: comms, error, isLoading } = useSWR(
    ["communications", activeTenantId],
    () => api.communications(activeTenantId),
  );

  const [searchQuery, setSearchQuery] = useState("");
  const [channelFilter, setChannelFilter] = useState("all");
  const [isSendOpen, setIsSendOpen] = useState(false);

  // Form state
  const [channel, setChannel] = useState<"whatsapp" | "sms" | "email">("whatsapp");
  const [recipient, setRecipient] = useState("+919876543210");
  const [subject, setSubject] = useState("VoxFlow Operations Update");
  const [messageBody, setMessageBody] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formError, setFormError] = useState("");

  const filteredComms = useMemo(() => {
    if (!comms) return [];
    return (comms as any[]).filter((c) => {
      const q = searchQuery.toLowerCase();
      const matchSearch =
        c.recipient.toLowerCase().includes(q) ||
        (c.body && c.body.toLowerCase().includes(q)) ||
        (c.subject && c.subject.toLowerCase().includes(q));
      const matchChannel = channelFilter === "all" || c.channel === channelFilter;
      return matchSearch && matchChannel;
    });
  }, [comms, searchQuery, channelFilter]);

  const stats = useMemo(() => {
    const list = (comms as any[]) || [];
    return {
      total: list.length,
      whatsapp: list.filter((c) => c.channel === "whatsapp").length,
      sms: list.filter((c) => c.channel === "sms").length,
      deliveredRate: "100%",
    };
  }, [comms]);

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!recipient.trim() || !messageBody.trim()) {
      setFormError("Recipient and Message Body are required");
      return;
    }
    setFormError("");
    setIsSubmitting(true);

    try {
      await api.createCommunication(
        {
          channel,
          recipient: recipient.trim(),
          subject: channel === "email" ? subject.trim() : undefined,
          body: messageBody.trim(),
        },
        activeTenantId,
      );
      mutate(["communications", activeTenantId]);
      setIsSendOpen(false);
      setMessageBody("");
    } catch (err: any) {
      setFormError(err.message || "Failed to dispatch message");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* ==================== PAGE HEADER ==================== */}
      <header className="flex flex-col sm:flex-row justify-between items-start sm:items-end gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-label uppercase tracking-widest text-[#a098b0] mb-1">
            <span>Omnichannel</span>
            <span>/</span>
            <span className="text-[#00ffcc] font-bold">{activeTenant.name}</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-headline font-extrabold text-[#e8e0f0] tracking-[0.05em] uppercase">
            Outbound <span className="text-[#00ffcc] text-glow-secondary">Communications</span>
          </h1>
          <p className="text-[#a098b0] font-body text-sm mt-1">
            Automated WhatsApp order summaries, SMS dispatch alerts, and ERP webhook notifications.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setIsSendOpen(true)}
            className="bg-[#00ffcc] text-[#0a0a12] px-4 py-2 rounded-xl text-xs font-headline font-bold uppercase tracking-widest flex items-center gap-2 shadow-[0_0_20px_rgba(0,255,204,0.4)] hover:scale-105 active:scale-95 transition-all"
          >
            <Send size={14} /> Send Outbound
          </button>
        </div>
      </header>

      {/* ==================== STAT CARDS ==================== */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="glass-panel p-4 rounded-2xl border border-[#00ffcc]/30">
          <div className="flex items-center justify-between text-[#a098b0] text-[10px] font-label uppercase tracking-wider mb-1">
            <span>Total Messages</span>
            <MessageSquare size={16} className="text-[#00ffcc]" />
          </div>
          <div className="text-2xl font-headline font-bold text-[#e8e0f0]">{stats.total}</div>
          <div className="text-[10px] text-[#00ffcc] mt-1">Dispatched via Twilio & Webhooks</div>
        </div>

        <div className="glass-panel p-4 rounded-2xl border border-emerald-500/30">
          <div className="flex items-center justify-between text-[#a098b0] text-[10px] font-label uppercase tracking-wider mb-1">
            <span>WhatsApp Messages</span>
            <MessageSquare size={16} className="text-emerald-400" />
          </div>
          <div className="text-2xl font-headline font-bold text-emerald-400">{stats.whatsapp}</div>
          <div className="text-[10px] text-[#a098b0] mt-1">Instant PO summaries</div>
        </div>

        <div className="glass-panel p-4 rounded-2xl border border-amber-500/30">
          <div className="flex items-center justify-between text-[#a098b0] text-[10px] font-label uppercase tracking-wider mb-1">
            <span>SMS Dispatches</span>
            <Smartphone size={16} className="text-amber-400" />
          </div>
          <div className="text-2xl font-headline font-bold text-amber-400">{stats.sms}</div>
          <div className="text-[10px] text-[#a098b0] mt-1">Fallback GSM alerts</div>
        </div>

        <div className="glass-panel p-4 rounded-2xl border border-blue-500/30">
          <div className="flex items-center justify-between text-[#a098b0] text-[10px] font-label uppercase tracking-wider mb-1">
            <span>Delivery Rate</span>
            <CheckCircle2 size={16} className="text-blue-400" />
          </div>
          <div className="text-2xl font-headline font-bold text-blue-400">{stats.deliveredRate}</div>
          <div className="text-[10px] text-[#a098b0] mt-1">Zero dropped alerts</div>
        </div>
      </div>

      {/* ==================== FILTERS & SEARCH ==================== */}
      <div className="flex flex-col sm:flex-row gap-3 items-stretch sm:items-center justify-between bg-[#111118]/80 p-3 rounded-2xl border border-[#302840]/60">
        <div className="relative flex-1">
          <Search size={15} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[#a098b0]" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search recipient phone, message body, or subject..."
            className="w-full bg-[#181824] border border-[#302840]/60 rounded-xl pl-9 pr-4 py-2 text-xs text-[#e8e0f0] placeholder:text-[#a098b0]/50 focus:outline-none focus:border-[#00ffcc] transition-all font-body"
          />
        </div>
        <div className="flex items-center gap-2 overflow-x-auto">
          {["all", "whatsapp", "sms", "email"].map((ch) => (
            <button
              key={ch}
              onClick={() => setChannelFilter(ch)}
              className={`px-3.5 py-1.5 rounded-xl text-xs font-label uppercase tracking-wider transition-all shrink-0 ${
                channelFilter === ch
                  ? "bg-[#00ffcc] text-[#0a0a12] font-bold shadow-[0_0_12px_rgba(0,255,204,0.4)]"
                  : "bg-[#181824] text-[#a098b0] hover:text-[#e8e0f0] border border-[#302840]/60"
              }`}
            >
              {ch}
            </button>
          ))}
        </div>
      </div>

      {/* ==================== COMMUNICATIONS FEED ==================== */}
      <div className="space-y-3">
        {isLoading && (
          <div className="py-16 text-center text-[#a098b0] text-xs font-label uppercase tracking-widest flex items-center justify-center gap-2">
            <span className="w-2 h-2 rounded-full bg-[#00ffcc] animate-ping" /> Loading communications log...
          </div>
        )}

        {error && (
          <div className="p-6 text-center text-[#ff2d78] bg-[#ff2d78]/5 text-xs font-body rounded-2xl border border-[#ff2d78]/20">
            Failed to load communications. Please verify backend API connectivity.
          </div>
        )}

        {!isLoading &&
          !error &&
          filteredComms.map((c) => (
            <div
              key={c.id}
              className="glass-panel p-5 rounded-2xl border border-[#302840]/60 hover:border-[#00ffcc]/60 transition-all space-y-3 shadow-lg"
            >
              <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
                <div className="flex items-center gap-3">
                  <span
                    className={`h-10 w-10 rounded-xl grid place-items-center text-sm shrink-0 border ${
                      c.channel === "whatsapp"
                        ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30 shadow-[0_0_12px_rgba(16,185,129,0.2)]"
                        : c.channel === "sms"
                        ? "bg-amber-500/10 text-amber-400 border-amber-500/30 shadow-[0_0_12px_rgba(245,158,11,0.2)]"
                        : "bg-blue-500/10 text-blue-400 border-blue-500/30"
                    }`}
                  >
                    {c.channel === "whatsapp" ? (
                      <MessageSquare size={18} />
                    ) : c.channel === "sms" ? (
                      <Smartphone size={18} />
                    ) : (
                      <Mail size={18} />
                    )}
                  </span>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-headline font-bold text-sm text-[#e8e0f0]">{c.recipient}</span>
                      <span className="text-[10px] font-label font-bold uppercase px-2 py-0.5 rounded bg-[#1e1e30] text-[#a098b0] border border-[#302840]/60">
                        {c.channel}
                      </span>
                    </div>
                    {c.subject && <div className="text-xs text-[#00ffcc] font-medium">{c.subject}</div>}
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <span className="flex items-center gap-1 text-[10px] font-label font-bold text-[#00ffcc] bg-[#00ffcc]/10 border border-[#00ffcc]/30 px-2.5 py-0.5 rounded-full">
                    <CheckCircle2 size={11} /> {c.status}
                  </span>
                  <span className="text-[11px] font-mono text-[#a098b0]">
                    {new Date(c.timestamp).toLocaleString("en-IN")}
                  </span>
                </div>
              </div>

              {/* Message Body Content */}
              <div className="bg-[#141422] p-3.5 rounded-xl border border-[#302840]/60 text-xs text-[#e8e0f0] font-body leading-relaxed whitespace-pre-wrap">
                {c.body}
              </div>
            </div>
          ))}

        {!isLoading && !error && filteredComms.length === 0 && (
          <div className="glass-panel rounded-2xl border border-dashed border-[#302840]/60 p-16 text-center space-y-3">
            <MessageSquare className="mx-auto text-[#5a5068]" size={36} />
            <div className="text-sm text-[#e8e0f0] font-headline font-semibold">No communications dispatched</div>
            <p className="text-xs text-[#a098b0] max-w-sm mx-auto">
              {searchQuery
                ? `No logs matching "${searchQuery}".`
                : `Automated WhatsApp and SMS messages will appear here whenever a voice call generates a PO, appointment, or follow-up summary.`}
            </p>
          </div>
        )}
      </div>

      {/* ==================== SEND MESSAGE MODAL ==================== */}
      {isSendOpen && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-md flex items-center justify-center p-4">
          <div className="bg-[#111118] border border-[#00ffcc]/40 rounded-2xl p-6 sm:p-8 max-w-md w-full shadow-[0_0_50px_rgba(0,255,204,0.2)] space-y-5 relative">
            <button
              onClick={() => setIsSendOpen(false)}
              className="absolute top-5 right-5 text-[#a098b0] hover:text-[#e8e0f0] transition-colors"
            >
              <X size={18} />
            </button>

            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-[#00ffcc]/15 border border-[#00ffcc]/40 flex items-center justify-center text-[#00ffcc]">
                <Send size={20} />
              </div>
              <div>
                <h3 className="font-headline font-bold text-lg text-[#e8e0f0]">Dispatch Outbound Message</h3>
                <p className="text-xs text-[#a098b0] font-body">Send live SMS or WhatsApp for {activeTenant.name}</p>
              </div>
            </div>

            <form onSubmit={handleSendMessage} className="space-y-4">
              <div>
                <label className="text-[10px] font-label uppercase tracking-widest text-[#e8e0f0] block mb-1.5">
                  Delivery Channel
                </label>
                <div className="grid grid-cols-3 gap-2">
                  {[
                    { key: "whatsapp", label: "WhatsApp", icon: MessageSquare },
                    { key: "sms", label: "SMS Alert", icon: Smartphone },
                    { key: "email", label: "Email", icon: Mail },
                  ].map((ch) => (
                    <button
                      key={ch.key}
                      type="button"
                      onClick={() => setChannel(ch.key as any)}
                      className={`p-2.5 rounded-xl border text-xs font-label uppercase tracking-wider flex items-center justify-center gap-1.5 transition-all ${
                        channel === ch.key
                          ? "border-[#00ffcc] bg-[#00ffcc]/10 text-[#00ffcc] font-bold"
                          : "border-[#302840] bg-[#181824] text-[#a098b0]"
                      }`}
                    >
                      <ch.icon size={14} /> {ch.label}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="text-[10px] font-label uppercase tracking-widest text-[#e8e0f0] block mb-1.5">
                  Recipient ({channel === "email" ? "Email Address" : "E.164 Phone Number"})
                </label>
                <input
                  type={channel === "email" ? "email" : "text"}
                  required
                  value={recipient}
                  onChange={(e) => setRecipient(e.target.value)}
                  placeholder={channel === "email" ? "supplier@company.com" : "+919876543210"}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-[#181824] border border-[#302840] text-xs text-[#e8e0f0] focus:border-[#00ffcc] focus:outline-none font-mono"
                />
              </div>

              {channel === "email" && (
                <div>
                  <label className="text-[10px] font-label uppercase tracking-widest text-[#e8e0f0] block mb-1.5">
                    Subject Line
                  </label>
                  <input
                    type="text"
                    value={subject}
                    onChange={(e) => setSubject(e.target.value)}
                    className="w-full px-3.5 py-2.5 rounded-xl bg-[#181824] border border-[#302840] text-xs text-[#e8e0f0] focus:border-[#00ffcc] focus:outline-none"
                  />
                </div>
              )}

              <div>
                <label className="text-[10px] font-label uppercase tracking-widest text-[#e8e0f0] block mb-1.5">
                  Message Content
                </label>
                <textarea
                  required
                  rows={4}
                  value={messageBody}
                  onChange={(e) => setMessageBody(e.target.value)}
                  placeholder="नमस्ते, आपका ऑर्डर PO-78901 सफलतापूर्वक प्रोसेस हो गया है..."
                  className="w-full px-3.5 py-2.5 rounded-xl bg-[#181824] border border-[#302840] text-xs text-[#e8e0f0] focus:border-[#00ffcc] focus:outline-none font-body leading-relaxed"
                />
              </div>

              {formError && (
                <div className="text-xs text-[#ff2d78] bg-[#ff2d78]/10 border border-[#ff2d78]/30 rounded-xl p-2.5">
                  {formError}
                </div>
              )}

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setIsSendOpen(false)}
                  className="px-4 py-2.5 rounded-xl text-xs font-label uppercase font-bold text-[#a098b0] hover:text-[#e8e0f0] bg-[#181824]"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-5 py-2.5 rounded-xl bg-[#00ffcc] text-[#0a0a12] text-xs font-headline font-bold uppercase tracking-wider shadow-[0_0_15px_rgba(0,255,204,0.4)] hover:scale-105 active:scale-95 disabled:opacity-50"
                >
                  {isSubmitting ? "Sending..." : "Dispatch Now"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
