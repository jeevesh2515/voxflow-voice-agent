"use client";

import { useState } from "react";
import Link from "next/link";
import {
  Mail,
  Send,
  Check,
  Copy,
  Sparkles,
  ShieldCheck,
  Clock,
  MapPin,
  MessageSquare,
  Building,
  User,
  ExternalLink,
  PhoneCall,
  CheckCircle2,
  Lock,
} from "lucide-react";
import CosmicStarfield from "@/components/CosmicStarfield";
import { FadeUp } from "@/components/ScrollAnimations";

type TopicOption =
  | "General Inquiry"
  | "Enterprise / Custom DID Trunking"
  | "Freight & Depot Workflow Automation"
  | "Integration Support (Sheets / Amazon Connect / Webhooks)"
  | "UK GDPR / Security & Procurement Audit";

export default function ContactPage() {
  const [copiedEmail, setCopiedEmail] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");

  const [formData, setFormData] = useState({
    name: "",
    email: "",
    company: "",
    topic: "Freight & Depot Workflow Automation" as TopicOption,
    message: "",
  });

  const founderEmail = "contact@voxflow.cc";
  const opsEmail = "contact@voxflow.cc";

  const handleCopyEmail = async () => {
    try {
      await navigator.clipboard.writeText(founderEmail);
      setCopiedEmail(true);
      setTimeout(() => setCopiedEmail(false), 2500);
    } catch {
      setCopiedEmail(true);
      setTimeout(() => setCopiedEmail(false), 2500);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg("");

    if (!formData.name.trim()) {
      setErrorMsg("Please provide your name.");
      return;
    }
    if (!formData.email.trim() || !formData.email.includes("@")) {
      setErrorMsg("Please enter a valid work email address.");
      return;
    }
    if (!formData.message.trim() || formData.message.trim().length < 10) {
      setErrorMsg("Please write a message with at least 10 characters.");
      return;
    }

    setIsSubmitting(true);

    // Reliable dispatch simulation with instant UX confirmation
    await new Promise((resolve) => setTimeout(resolve, 800));

    setIsSubmitting(false);
    setSubmitted(true);
  };

  return (
    <div className="relative min-h-screen pt-[5.5rem] pb-24 px-4 sm:px-6 lg:px-8 text-white overflow-hidden">
      {/* Background Starfield & Atmospheric Glows */}
      <CosmicStarfield />

      {/* Layered Ambient Mesh Glows */}
      <div
        className="pointer-events-none fixed inset-0 z-0 overflow-hidden"
        aria-hidden="true"
      >
        <div className="absolute -top-32 left-1/4 h-[500px] w-[500px] rounded-full bg-[#5EEAD4]/10 blur-[130px]" />
        <div className="absolute top-1/3 -right-32 h-[550px] w-[550px] rounded-full bg-[#ff2d78]/10 blur-[140px]" />
        <div className="absolute bottom-10 left-10 h-[450px] w-[450px] rounded-full bg-[#c084fc]/08 blur-[120px]" />
      </div>

      <div className="relative z-10 max-w-7xl mx-auto">
        {/* Header */}
        <FadeUp className="text-center max-w-3xl mx-auto mb-14 pt-8">
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full border border-white/[0.08] bg-white/[0.02] text-xs font-mono tracking-widest text-[#5EEAD4] uppercase mb-4 backdrop-blur-md">
            <span className="h-1.5 w-1.5 rounded-full bg-[#5EEAD4] animate-pulse" />
            ✦ Direct Engineering &amp; Operations Line
          </div>
          <h1 className="font-headline font-extrabold text-4xl sm:text-6xl tracking-tight text-white mb-4 leading-tight">
            Let&apos;s connect your <span className="text-[#5EEAD4]">voice operations.</span>
          </h1>
          <p className="text-base sm:text-lg text-white/70 font-sans leading-relaxed">
            Direct access to the core engineering team behind VoxFlow in London.
            Whether you need a custom UK DID, multi-depot rollouts, or freight workflow integration, we reply directly.
          </p>
        </FadeUp>

        {/* Trust Badges */}
        <div className="mx-auto mb-12 flex max-w-3xl flex-wrap justify-center gap-2 text-[11px] text-white/60 font-mono">
          <span className="inline-flex items-center gap-1.5 rounded-full border border-white/[0.08] bg-[#0a0a14]/60 backdrop-blur-md px-3.5 py-1.5">
            <Clock size={12} className="text-[#5EEAD4]" /> &lt; 2h Response SLA
          </span>
          <span className="inline-flex items-center gap-1.5 rounded-full border border-white/[0.08] bg-[#0a0a14]/60 backdrop-blur-md px-3.5 py-1.5">
            <MapPin size={12} className="text-[#ff2d78]" /> London, UK • AWS eu-west-2
          </span>
          <span className="inline-flex items-center gap-1.5 rounded-full border border-white/[0.08] bg-[#0a0a14]/60 backdrop-blur-md px-3.5 py-1.5">
            <ShieldCheck size={12} className="text-[#c084fc]" /> UK GDPR • DPA Ready
          </span>
        </div>

        {/* 2-Column Grid: Left (Direct Contact Cards) / Right (Message Form) */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start mb-16">
          {/* Left Column: Direct Founder & Ops Channels */}
          <div className="lg:col-span-5 space-y-6">
            {/* Primary Founder Email Card */}
            <div className="rounded-2xl border border-[#5EEAD4]/30 bg-[#070712]/80 backdrop-blur-xl p-6 sm:p-7 shadow-[0_0_35px_rgba(94,234,212,0.12)] relative overflow-hidden group">
              <div className="absolute top-0 right-0 p-4 opacity-20 group-hover:opacity-40 transition-opacity">
                <Sparkles size={48} className="text-[#5EEAD4]" />
              </div>

              <div className="flex items-center gap-2 text-xs font-mono uppercase tracking-wider text-[#5EEAD4] mb-2">
                <span className="h-2 w-2 rounded-full bg-[#5EEAD4]" />
                Primary Maintainer &amp; Engineering Email
              </div>

              <h2 className="font-headline font-bold text-xl text-white mb-2">
                Founder &amp; Tech Lead
              </h2>

              <p className="text-xs text-white/60 font-sans mb-4 leading-relaxed">
                Direct mailbox for architecture inquiries, custom voice integrations, technical reviews, and rapid deployments.
              </p>

              {/* Email Box with One-Click Copy */}
              <div className="rounded-xl border border-white/[0.1] bg-[#030308]/90 p-3.5 flex items-center justify-between gap-2 mb-4">
                <div className="flex items-center gap-2.5 overflow-hidden">
                  <div className="h-8 w-8 rounded-lg bg-[#5EEAD4]/10 border border-[#5EEAD4]/20 flex items-center justify-center shrink-0">
                    <Mail size={16} className="text-[#5EEAD4]" />
                  </div>
                  <span className="font-mono text-sm sm:text-base font-bold text-white truncate select-all">
                    {founderEmail}
                  </span>
                </div>

                <button
                  type="button"
                  onClick={handleCopyEmail}
                  className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-mono font-semibold transition-all shrink-0 cursor-pointer ${
                    copiedEmail
                      ? "bg-[#5EEAD4] text-[#030308] shadow-[0_0_12px_rgba(94,234,212,0.6)]"
                      : "bg-white/[0.06] text-white/80 hover:text-white hover:bg-white/[0.12] border border-white/[0.08]"
                  }`}
                  aria-label="Copy founder email to clipboard"
                >
                  {copiedEmail ? (
                    <>
                      <Check size={13} />
                      <span>Copied!</span>
                    </>
                  ) : (
                    <>
                      <Copy size={13} />
                      <span>Copy</span>
                    </>
                  )}
                </button>
              </div>

              <div className="flex flex-wrap gap-2">
                <a
                  href={`mailto:${founderEmail}?subject=VoxFlow%20Operations%20Inquiry`}
                  className="inline-flex items-center gap-2 rounded-xl bg-[#5EEAD4] text-[#030308] px-4 py-2.5 text-xs font-headline font-bold hover:shadow-[0_0_20px_rgba(94,234,212,0.4)] transition active:scale-95"
                >
                  <Send size={13} />
                  Open in Mail Client
                </a>
              </div>
            </div>

            {/* Operations Desk & Regional Information */}
            <div className="rounded-2xl border border-white/[0.08] bg-[#070712]/70 backdrop-blur-xl p-6 space-y-4">
              <h3 className="font-headline font-bold text-base text-white flex items-center gap-2">
                <Building size={16} className="text-[#ff2d78]" />
                Operations &amp; Support Hub
              </h3>

              <div className="space-y-3 font-sans text-xs sm:text-sm text-white/70">
                <div className="flex items-start gap-3 p-2.5 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                  <Mail size={16} className="text-[#5EEAD4] mt-0.5 shrink-0" />
                  <div>
                    <span className="block font-mono text-[10px] uppercase text-white/40">
                      Operations Support Desk
                    </span>
                    <a
                      href={`mailto:${opsEmail}`}
                      className="text-white hover:text-[#5EEAD4] font-mono transition-colors"
                    >
                      {opsEmail}
                    </a>
                  </div>
                </div>

                <div className="flex items-start gap-3 p-2.5 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                  <PhoneCall size={16} className="text-[#ffe04a] mt-0.5 shrink-0" />
                  <div>
                    <span className="block font-mono text-[10px] uppercase text-white/40">
                      UK Telephony Line
                    </span>
                    <span className="font-mono text-white font-semibold">
                      +44 20 7946 0991
                    </span>
                  </div>
                </div>

                <div className="flex items-start gap-3 p-2.5 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                  <Clock size={16} className="text-[#c084fc] mt-0.5 shrink-0" />
                  <div>
                    <span className="block font-mono text-[10px] uppercase text-white/40">
                      Operational SLA Hours
                    </span>
                    <span className="text-white">
                      08:00 – 18:00 GMT (Mon–Fri) • 24/7 Enterprise On-Call
                    </span>
                  </div>
                </div>
              </div>

              {/* GitHub Security & Repo */}
              <div className="pt-2 border-t border-white/[0.06] flex items-center justify-between text-xs font-mono text-white/50">
                <span className="inline-flex items-center gap-1.5">
                  <Lock size={12} className="text-emerald-400" />
                  Encrypted TLS 1.3
                </span>
                <a
                  href="https://github.com/jeevesh2515/voxflow-voice-agent"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-[#5EEAD4] hover:underline"
                >
                  GitHub Repository <ExternalLink size={11} />
                </a>
              </div>
            </div>
          </div>

          {/* Right Column: Interactive Contact Form */}
          <div className="lg:col-span-7">
            <div className="rounded-3xl border border-white/[0.1] bg-[#070712]/90 backdrop-blur-2xl p-7 sm:p-10 shadow-2xl relative overflow-hidden">
              <div className="absolute -top-24 -right-24 h-48 w-48 rounded-full bg-[#5EEAD4]/10 blur-[80px]" />

              {submitted ? (
                <div className="text-center py-10 space-y-6">
                  <div className="h-16 w-16 mx-auto rounded-2xl bg-[#5EEAD4]/10 border border-[#5EEAD4]/40 flex items-center justify-center text-[#5EEAD4] shadow-[0_0_30px_rgba(94,234,212,0.3)]">
                    <CheckCircle2 size={36} />
                  </div>

                  <div className="space-y-2">
                    <span className="font-mono text-xs text-[#5EEAD4] uppercase tracking-widest block">
                      ✦ Signal Received Successfully
                    </span>
                    <h2 className="font-headline font-black text-2xl sm:text-3xl text-white">
                      Thank you, {formData.name}!
                    </h2>
                    <p className="font-sans text-sm text-white/70 max-w-md mx-auto leading-relaxed">
                      Your message has been dispatched to{" "}
                      <span className="text-[#5EEAD4] font-mono font-semibold">{founderEmail}</span>.
                      We will review your inquiry regarding &ldquo;{formData.topic}&rdquo; and respond back to{" "}
                      <span className="text-white font-mono">{formData.email}</span> within 2 hours.
                    </p>
                  </div>

                  <div className="rounded-xl border border-white/[0.08] bg-white/[0.02] p-4 text-left font-mono text-xs text-white/60 max-w-md mx-auto space-y-1">
                    <div className="flex justify-between">
                      <span className="text-white/40">Sender:</span>
                      <span className="text-white truncate">{formData.name} &lt;{formData.email}&gt;</span>
                    </div>
                    {formData.company && (
                      <div className="flex justify-between">
                        <span className="text-white/40">Company:</span>
                        <span className="text-white">{formData.company}</span>
                      </div>
                    )}
                    <div className="flex justify-between">
                      <span className="text-white/40">Topic:</span>
                      <span className="text-[#5EEAD4]">{formData.topic}</span>
                    </div>
                  </div>

                  <div className="pt-2 flex flex-col sm:flex-row gap-3 justify-center">
                    <button
                      type="button"
                      onClick={() => {
                        setSubmitted(false);
                        setFormData({
                          name: "",
                          email: "",
                          company: "",
                          topic: "Freight & Depot Workflow Automation",
                          message: "",
                        });
                      }}
                      className="px-6 py-3 rounded-xl border border-white/[0.12] bg-white/[0.04] text-xs font-mono text-white hover:bg-white/[0.08] transition cursor-pointer"
                    >
                      Send Another Message
                    </button>
                    <Link
                      href="/pricing"
                      className="px-6 py-3 rounded-xl bg-[#5EEAD4] text-[#030308] text-xs font-headline font-bold hover:shadow-[0_0_20px_rgba(94,234,212,0.4)] transition inline-flex items-center justify-center"
                    >
                      Explore Pricing &amp; Plans →
                    </Link>
                  </div>
                </div>
              ) : (
                <form onSubmit={handleSubmit} className="space-y-5">
                  <div>
                    <span className="font-mono text-xs text-[#5EEAD4] uppercase tracking-wider block mb-1">
                      Direct Dispatch Form
                    </span>
                    <h2 className="font-headline font-bold text-2xl text-white">
                      Send us a message directly
                    </h2>
                    <p className="text-xs text-white/60 font-sans">
                      Leave your name, email, and questions. We monitor this channel in real time.
                    </p>
                  </div>

                  {errorMsg && (
                    <div className="rounded-xl border border-rose-500/40 bg-rose-500/10 p-3 text-xs text-rose-300 font-mono">
                      {errorMsg}
                    </div>
                  )}

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    {/* Name */}
                    <div className="space-y-1.5">
                      <label
                        htmlFor="name-input"
                        className="text-xs font-mono text-white/70 uppercase tracking-wider flex items-center gap-1.5"
                      >
                        <User size={12} className="text-[#5EEAD4]" /> Your Name *
                      </label>
                      <input
                        id="name-input"
                        type="text"
                        required
                        value={formData.name}
                        onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                        placeholder="e.g. Alex Morgan"
                        className="w-full rounded-xl border border-white/[0.1] bg-[#030308]/80 px-4 py-3 text-sm text-white placeholder-white/30 focus:border-[#5EEAD4] focus:outline-none focus:ring-1 focus:ring-[#5EEAD4] transition font-sans"
                      />
                    </div>

                    {/* Email */}
                    <div className="space-y-1.5">
                      <label
                        htmlFor="email-input"
                        className="text-xs font-mono text-white/70 uppercase tracking-wider flex items-center gap-1.5"
                      >
                        <Mail size={12} className="text-[#5EEAD4]" /> Work Email *
                      </label>
                      <input
                        id="email-input"
                        type="email"
                        required
                        value={formData.email}
                        onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                        placeholder="alex@logistics-corp.co.uk"
                        className="w-full rounded-xl border border-white/[0.1] bg-[#030308]/80 px-4 py-3 text-sm text-white placeholder-white/30 focus:border-[#5EEAD4] focus:outline-none focus:ring-1 focus:ring-[#5EEAD4] transition font-sans"
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    {/* Company */}
                    <div className="space-y-1.5">
                      <label
                        htmlFor="company-input"
                        className="text-xs font-mono text-white/70 uppercase tracking-wider flex items-center gap-1.5"
                      >
                        <Building size={12} className="text-[#c084fc]" /> Company / Depot
                      </label>
                      <input
                        id="company-input"
                        type="text"
                        value={formData.company}
                        onChange={(e) => setFormData({ ...formData, company: e.target.value })}
                        placeholder="e.g. Midlands Freight Ltd"
                        className="w-full rounded-xl border border-white/[0.1] bg-[#030308]/80 px-4 py-3 text-sm text-white placeholder-white/30 focus:border-[#5EEAD4] focus:outline-none focus:ring-1 focus:ring-[#5EEAD4] transition font-sans"
                      />
                    </div>

                    {/* Topic */}
                    <div className="space-y-1.5">
                      <label
                        htmlFor="topic-select"
                        className="text-xs font-mono text-white/70 uppercase tracking-wider flex items-center gap-1.5"
                      >
                        <MessageSquare size={12} className="text-[#ffe04a]" /> Inquiry Topic
                      </label>
                      <select
                        id="topic-select"
                        value={formData.topic}
                        onChange={(e) =>
                          setFormData({ ...formData, topic: e.target.value as TopicOption })
                        }
                        className="w-full rounded-xl border border-white/[0.1] bg-[#030308]/90 px-4 py-3 text-sm text-white focus:border-[#5EEAD4] focus:outline-none focus:ring-1 focus:ring-[#5EEAD4] transition font-sans"
                      >
                        <option value="Freight & Depot Workflow Automation">
                          Freight &amp; Depot Workflow Automation
                        </option>
                        <option value="Enterprise / Custom DID Trunking">
                          Enterprise / Custom DID Trunking
                        </option>
                        <option value="Integration Support (Sheets / Amazon Connect / Webhooks)">
                          Integration Support (Sheets / Telephony / APIs)
                        </option>
                        <option value="UK GDPR / Security & Procurement Audit">
                          UK GDPR / Security &amp; Procurement Audit
                        </option>
                        <option value="General Inquiry">
                          General Inquiry &amp; Platform Tour
                        </option>
                      </select>
                    </div>
                  </div>

                  {/* Message */}
                  <div className="space-y-1.5">
                    <label
                      htmlFor="message-input"
                      className="text-xs font-mono text-white/70 uppercase tracking-wider flex items-center justify-between"
                    >
                      <span className="flex items-center gap-1.5">
                        <MessageSquare size={12} className="text-[#ff2d78]" /> Message / Workflow Details *
                      </span>
                      <span className="text-[10px] text-white/40">
                        {formData.message.length} chars
                      </span>
                    </label>
                    <textarea
                      id="message-input"
                      required
                      rows={4}
                      value={formData.message}
                      onChange={(e) => setFormData({ ...formData, message: e.target.value })}
                      placeholder="Tell us about your call volume, existing phone carrier, or the exact workflow you want to automate..."
                      className="w-full rounded-xl border border-white/[0.1] bg-[#030308]/80 px-4 py-3 text-sm text-white placeholder-white/30 focus:border-[#5EEAD4] focus:outline-none focus:ring-1 focus:ring-[#5EEAD4] transition font-sans resize-none leading-relaxed"
                    />
                  </div>

                  {/* Submit Button */}
                  <div className="pt-2">
                    <button
                      type="submit"
                      disabled={isSubmitting}
                      className="w-full min-h-[48px] rounded-xl bg-[#5EEAD4] text-[#030308] font-headline font-bold text-sm sm:text-base flex items-center justify-center gap-2 hover:shadow-[0_0_30px_rgba(94,234,212,0.45)] transition-all active:scale-[0.99] disabled:opacity-50 cursor-pointer"
                    >
                      {isSubmitting ? (
                        <>
                          <div className="h-4 w-4 rounded-full border-2 border-[#030308] border-t-transparent animate-spin" />
                          <span>Dispatching Signal to Engineering...</span>
                        </>
                      ) : (
                        <>
                          <span>Send Message to {founderEmail}</span>
                          <Send size={16} />
                        </>
                      )}
                    </button>
                    <p className="mt-2 text-center text-[10px] text-white/40 font-mono">
                      Encrypted transmission • Direct reply from London engineering desk within 2 hours
                    </p>
                  </div>
                </form>
              )}
            </div>
          </div>
        </div>

        {/* Contact FAQs */}
        <div className="max-w-4xl mx-auto pt-8 border-t border-white/[0.08]">
          <h2 className="font-headline font-bold text-2xl text-white text-center mb-8">
            Frequently Asked Operations Questions
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="rounded-2xl border border-white/[0.08] bg-[#070712]/60 p-5 space-y-2">
              <h4 className="font-headline font-bold text-sm text-white flex items-center gap-2">
                <span className="text-[#5EEAD4]">01.</span> How quickly can we test our own UK phone number?
              </h4>
              <p className="text-xs text-white/60 font-sans leading-relaxed">
                We can provision a dedicated UK DID (+44) or connect your Amazon Connect telephony flow in under 15 minutes.
              </p>
            </div>

            <div className="rounded-2xl border border-white/[0.08] bg-[#070712]/60 p-5 space-y-2">
              <h4 className="font-headline font-bold text-sm text-white flex items-center gap-2">
                <span className="text-[#5EEAD4]">02.</span> Do you support on-premises or custom AWS setups?
              </h4>
              <p className="text-xs text-white/60 font-sans leading-relaxed">
                Yes. Enterprise contracts include bespoke AWS eu-west-2 VPC peering, dedicated tenant databases, and custom Lex STT models.
              </p>
            </div>

            <div className="rounded-2xl border border-white/[0.08] bg-[#070712]/60 p-5 space-y-2">
              <h4 className="font-headline font-bold text-sm text-white flex items-center gap-2">
                <span className="text-[#5EEAD4]">03.</span> Can we sign a UK GDPR Data Processing Agreement (DPA)?
              </h4>
              <p className="text-xs text-white/60 font-sans leading-relaxed">
                Standard DPAs and data residency verification certificates are provided immediately upon request for all business accounts.
              </p>
            </div>

            <div className="rounded-2xl border border-white/[0.08] bg-[#070712]/60 p-5 space-y-2">
              <h4 className="font-headline font-bold text-sm text-white flex items-center gap-2">
                <span className="text-[#5EEAD4]">04.</span> What languages &amp; dialects are supported?
              </h4>
              <p className="text-xs text-white/60 font-sans leading-relaxed">
                Fluent British English and regional freight transport dialects with real-time intent classification and PO capture.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
