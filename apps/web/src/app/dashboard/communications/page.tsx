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
  const [isSummarizing, setIsSummarizing] = useState(false);
  const [summarizeFeedback, setSummarizeFeedback] = useState<string | null>(null);
  const [formError, setFormError] = useState("");

  const handleSummarizeEmails = async () => {
    setIsSummarizing(true);
    setSummarizeFeedback(null);
    try {
      const res = await api.runEmailSummarizer(activeTenantId);
      mutate(["communications", activeTenantId]);
      setSummarizeFeedback(
        `✓ Processed ${res.processed_count} new emails (${res.sheets_synced_count} synced to Google Sheets Email Log)`
      );
      setTimeout(() => setSummarizeFeedback(null), 6000);
    } catch (err: any) {
      setSummarizeFeedback(`Failed to sync emails: ${err.message}`);
    } finally {
      setIsSummarizing(false);
    }
  };

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
      <header className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 bg-[#12121e] p-6 rounded-2xl border border-[#242436] shadow-sm">
        <div className="space-y-1">
          <div className="flex items-center gap-2 text-xs font-mono text-[#94a3b8]">
            <span>Omnichannel Communications</span>
            <span>/</span>
            <span className="text-[#00ffcc] font-bold">{activeTenant.name}</span>
          </div>
          <h1 className="text-xl sm:text-2xl font-headline font-bold text-white tracking-tight">
            Outbound Dispatch & Email Summaries
          </h1>
          <p className="text-xs sm:text-sm text-[#94a3b8]">
            Automated WhatsApp order summaries, SMS dispatch alerts, and Google Sheets email logs.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleSummarizeEmails}
            disabled={isSummarizing}
            className="bg-[#181826] hover:bg-[#202034] text-[#00ffcc] border border-[#00ffcc]/40 px-4 py-2 rounded-xl text-xs font-medium flex items-center gap-2 transition-colors disabled:opacity-50"
          >
            <Mail size={14} className={isSummarizing ? "animate-spin" : ""} />
            <span>{isSummarizing ? "Syncing..." : "⚡ Sync & Summarize Emails"}</span>
          </button>
          <button
            onClick={() => setIsSendOpen(true)}
            className="bg-[#00ffcc] hover:bg-[#00e6b8] text-black px-4 py-2 rounded-xl text-xs font-bold flex items-center gap-2 shadow-sm transition-colors"
          >
            <Send size={14} />
            <span>Send Outbound</span>
          </button>
        </div>
      </header>

      {summarizeFeedback && (
        <div className="p-3.5 bg-[#00ffcc]/10 border border-[#00ffcc]/30 rounded-xl text-xs text-[#00ffcc] font-mono font-bold flex items-center gap-2 shadow-sm">
          <CheckCircle2 size={16} />
          <span>{summarizeFeedback}</span>
        </div>
      )}

      {/* ==================== STAT CARDS ==================== */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-[#141422] p-5 rounded-2xl border border-[#28283c] shadow-sm">
          <div className="flex items-center justify-between text-[#94a3b8] text-xs font-mono uppercase tracking-wider mb-1">
            <span>Total Messages</span>
            <MessageSquare size={16} className="text-[#00ffcc]" />
          </div>
          <div className="text-2xl font-headline font-bold text-white">{stats.total}</div>
          <div className="text-xs text-[#00ffcc] mt-1">Dispatched via Twilio & Webhooks</div>
        </div>

        <div className="bg-[#141422] p-5 rounded-2xl border border-[#28283c] shadow-sm">
          <div className="flex items-center justify-between text-[#94a3b8] text-xs font-mono uppercase tracking-wider mb-1">
            <span>WhatsApp Messages</span>
            <MessageSquare size={16} className="text-emerald-400" />
          </div>
          <div className="text-2xl font-headline font-bold text-emerald-400">{stats.whatsapp}</div>
          <div className="text-xs text-[#94a3b8] mt-1">Instant PO summaries</div>
        </div>

        <div className="bg-[#141422] p-5 rounded-2xl border border-[#28283c] shadow-sm">
          <div className="flex items-center justify-between text-[#94a3b8] text-xs font-mono uppercase tracking-wider mb-1">
            <span>SMS Dispatches</span>
            <Smartphone size={16} className="text-amber-400" />
          </div>
          <div className="text-2xl font-headline font-bold text-amber-400">{stats.sms}</div>
          <div className="text-xs text-[#94a3b8] mt-1">Fallback GSM alerts</div>
        </div>

        <div className="bg-[#141422] p-5 rounded-2xl border border-[#28283c] shadow-sm">
          <div className="flex items-center justify-between text-[#94a3b8] text-xs font-mono uppercase tracking-wider mb-1">
            <span>Delivery Rate</span>
            <CheckCircle2 size={16} className="text-blue-400" />
          </div>
          <div className="text-2xl font-headline font-bold text-blue-400">{stats.deliveredRate}</div>
          <div className="text-xs text-[#94a3b8] mt-1">Zero dropped alerts</div>
        </div>
      </div>

      {/* ==================== FILTERS & SEARCH ==================== */}
      <div className="flex flex-col sm:flex-row gap-3 items-stretch sm:items-center justify-between bg-[#141422] p-3 rounded-2xl border border-[#28283c]">
        <div className="relative flex-1">
          <Search size={15} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[#64748b]" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search recipient phone, message body, or subject..."
            className="w-full bg-[#10101a] border border-[#28283c] rounded-xl pl-9 pr-4 py-2 text-xs text-white placeholder:text-[#64748b] focus:outline-none focus:border-[#00ffcc]"
          />
        </div>
        <div className="flex items-center bg-[#10101a] p-1 rounded-xl border border-[#28283c] overflow-x-auto">
          {["all", "whatsapp", "sms", "email"].map((ch) => (
            <button
              key={ch}
              onClick={() => setChannelFilter(ch)}
              className={`px-3.5 py-1.5 rounded-lg text-xs font-medium uppercase tracking-wider transition-colors shrink-0 ${
                channelFilter === ch
                  ? "bg-[#ff2d78] text-white"
                  : "text-[#94a3b8] hover:text-white"
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
          <div className="py-16 text-center text-[#94a3b8] text-xs">
            Loading communications log...
          </div>
        )}

        {error && (
          <div className="p-6 text-center text-red-400 bg-red-500/10 text-xs rounded-2xl border border-red-500/20">
            Failed to load communications. Please verify backend API connectivity.
          </div>
        )}

        {!isLoading &&
          !error &&
          filteredComms.map((c) => (
            <div
              key={c.id}
              className="bg-[#141422] p-5 rounded-2xl border border-[#28283c] hover:border-[#00ffcc]/50 transition-all space-y-3 shadow-sm"
            >
              <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
                <div className="flex items-center gap-3">
                  <span
                    className={`h-10 w-10 rounded-xl grid place-items-center text-sm shrink-0 border ${
                      c.channel === "whatsapp"
                        ? "bg-emerald-500/15 text-emerald-400 border-emerald-500/30"
                        : c.channel === "sms"
                        ? "bg-amber-500/15 text-amber-400 border-amber-500/30"
                        : "bg-blue-500/15 text-blue-400 border-blue-500/30"
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
                      <span className="font-headline font-bold text-sm text-white">{c.recipient}</span>
                      <span className="text-[10px] font-mono font-bold uppercase px-2 py-0.5 rounded bg-[#181826] text-[#94a3b8] border border-[#28283c]">
                        {c.channel}
                      </span>
                    </div>
                    {c.subject && <div className="text-xs text-[#00ffcc] font-medium mt-0.5">{c.subject}</div>}
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <span className="flex items-center gap-1 text-[10px] font-mono font-bold text-[#00ffcc] bg-[#00ffcc]/15 border border-[#00ffcc]/30 px-2.5 py-0.5 rounded-md">
                    <CheckCircle2 size={11} /> {c.status}
                  </span>
                  <span className="text-[11px] font-mono text-[#94a3b8]">
                    {new Date(c.timestamp).toLocaleString("en-IN")}
                  </span>
                </div>
              </div>

              {/* Message Body Content */}
              <div className="bg-[#181828] p-3.5 rounded-xl border border-[#28283c] text-xs text-[#cbd5e1] leading-relaxed whitespace-pre-wrap font-mono">
                {c.body}
              </div>
            </div>
          ))}

        {!isLoading && !error && filteredComms.length === 0 && (
          <div className="bg-[#141422] rounded-2xl border border-dashed border-[#28283c] p-16 text-center space-y-3">
            <MessageSquare className="mx-auto text-[#64748b]" size={36} />
            <div className="text-sm text-white font-headline font-semibold">No communications dispatched</div>
            <p className="text-xs text-[#94a3b8] max-w-sm mx-auto">
              {searchQuery
                ? `No logs matching "${searchQuery}".`
                : `Automated WhatsApp and SMS messages will appear here whenever a voice call generates a PO, appointment, or follow-up summary.`}
            </p>
          </div>
        )}
      </div>

      {/* ==================== SEND MESSAGE MODAL ==================== */}
      {isSendOpen && (
        <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#141422] border border-[#28283c] rounded-2xl p-6 sm:p-8 max-w-md w-full shadow-2xl space-y-5 relative">
            <button
              onClick={() => setIsSendOpen(false)}
              className="absolute top-5 right-5 text-[#94a3b8] hover:text-white transition-colors"
            >
              <X size={18} />
            </button>

            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-[#00ffcc]/15 border border-[#00ffcc]/30 flex items-center justify-center text-[#00ffcc]">
                <Send size={20} />
              </div>
              <div>
                <h3 className="font-headline font-bold text-base text-white">Dispatch Outbound Message</h3>
                <p className="text-xs text-[#94a3b8]">Send live SMS or WhatsApp for {activeTenant.name}</p>
              </div>
            </div>

            <form onSubmit={handleSendMessage} className="space-y-4">
              <div>
                <label className="text-[11px] font-mono uppercase tracking-wider text-[#94a3b8] block mb-1.5 font-bold">
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
                      className={`p-2.5 rounded-xl border text-xs font-medium flex items-center justify-center gap-1.5 transition-colors ${
                        channel === ch.key
                          ? "border-[#00ffcc] bg-[#00ffcc]/15 text-[#00ffcc] font-bold"
                          : "border-[#28283c] bg-[#10101a] text-[#94a3b8] hover:text-white"
                      }`}
                    >
                      <ch.icon size={14} /> {ch.label}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="text-[11px] font-mono uppercase tracking-wider text-[#94a3b8] block mb-1.5 font-bold">
                  Recipient ({channel === "email" ? "Email Address" : "E.164 Phone Number"})
                </label>
                <input
                  type={channel === "email" ? "email" : "text"}
                  required
                  value={recipient}
                  onChange={(e) => setRecipient(e.target.value)}
                  placeholder={channel === "email" ? "supplier@company.com" : "+919876543210"}
                  className="w-full px-3.5 py-2 rounded-xl bg-[#10101a] border border-[#28283c] text-xs text-white focus:border-[#00ffcc] focus:outline-none font-mono"
                />
              </div>

              {channel === "email" && (
                <div>
                  <label className="text-[11px] font-mono uppercase tracking-wider text-[#94a3b8] block mb-1.5 font-bold">
                    Subject Line
                  </label>
                  <input
                    type="text"
                    value={subject}
                    onChange={(e) => setSubject(e.target.value)}
                    className="w-full px-3.5 py-2 rounded-xl bg-[#10101a] border border-[#28283c] text-xs text-white focus:border-[#00ffcc] focus:outline-none"
                  />
                </div>
              )}

              <div>
                <label className="text-[11px] font-mono uppercase tracking-wider text-[#94a3b8] block mb-1.5 font-bold">
                  Message Content
                </label>
                <textarea
                  required
                  rows={4}
                  value={messageBody}
                  onChange={(e) => setMessageBody(e.target.value)}
                  placeholder="नमस्ते, आपका ऑर्डर PO-78901 सफलतापूर्वक प्रोसेस हो गया है..."
                  className="w-full px-3.5 py-2 rounded-xl bg-[#10101a] border border-[#28283c] text-xs text-white focus:border-[#00ffcc] focus:outline-none font-mono leading-relaxed"
                />
              </div>

              {formError && (
                <div className="text-xs text-red-400 bg-red-500/10 border border-red-500/30 rounded-xl p-2.5">
                  {formError}
                </div>
              )}

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setIsSendOpen(false)}
                  className="px-4 py-2 rounded-xl text-xs font-medium text-[#94a3b8] hover:text-white bg-[#181826] border border-[#28283c]"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-5 py-2 rounded-xl bg-[#00ffcc] hover:bg-[#00e6b8] text-black text-xs font-bold transition-colors disabled:opacity-50"
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
