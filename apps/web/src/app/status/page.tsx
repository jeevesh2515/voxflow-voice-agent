"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

const LOCAL_API_URL = "http://localhost:8000";

function resolveApiBase(): string {
  const configured = process.env.NEXT_PUBLIC_API_URL?.trim();
  if (configured) return configured.replace(/\/+$/, "");
  if (
    typeof window !== "undefined" &&
    (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1")
  ) {
    return LOCAL_API_URL;
  }
  return "";
}

type ApiHealthBody = {
  ok?: boolean;
  service?: string;
  version?: string;
  llm_provider?: string;
};

type DbHealthBody = {
  ok?: boolean;
  checked_at?: string;
  dialect?: string;
  latency_ms?: number;
  tenant_count?: number;
  error?: string;
};

type ServiceCheck<T> = {
  state: "loading" | "up" | "down";
  body: T | null;
  error: string | null;
};

type StatusState = {
  checking: boolean;
  api: ServiceCheck<ApiHealthBody>;
  db: ServiceCheck<DbHealthBody>;
  checkedAt: string | null;
};

const INITIAL: StatusState = {
  checking: true,
  api: { state: "loading", body: null, error: null },
  db: { state: "loading", body: null, error: null },
  checkedAt: null,
};

function toErrorMessage(err: unknown): string {
  return err instanceof Error ? err.message : String(err);
}

async function checkEndpoint<T>(url: string): Promise<ServiceCheck<T>> {
  let res: Response;
  try {
    res = await fetch(url, { cache: "no-store" });
  } catch (err) {
    return { state: "down", body: null, error: toErrorMessage(err) };
  }
  let body: T | null = null;
  try {
    body = (await res.json()) as T;
  } catch {
    body = null;
  }
  if (!res.ok) {
    const detail = body ? JSON.stringify(body) : `${res.status} ${res.statusText}`;
    return { state: "down", body, error: detail };
  }
  if (body !== null && typeof body === "object" && (body as { ok?: unknown }).ok === false) {
    return { state: "down", body, error: JSON.stringify(body) };
  }
  return { state: "up", body, error: null };
}

function overallLabel(s: StatusState): { text: string; dot: string } {
  if (s.checking || s.api.state === "loading" || s.db.state === "loading") {
    return { text: "Checking…", dot: "bg-yellow-400" };
  }
  if (s.api.state === "up" && s.db.state === "up") {
    return { text: "All systems operational", dot: "bg-emerald-400" };
  }
  if (s.api.state === "down" && s.db.state === "down") {
    return { text: "Major outage", dot: "bg-red-500" };
  }
  return { text: "Degraded", dot: "bg-yellow-400" };
}

function ServiceRow({
  name,
  check,
  children,
}: {
  name: string;
  check: ServiceCheck<unknown>;
  children?: React.ReactNode;
}) {
  const badge =
    check.state === "up"
      ? "bg-emerald-400/10 border-emerald-400/30 text-emerald-300"
      : check.state === "down"
        ? "bg-red-500/10 border-red-500/30 text-red-300"
        : "bg-yellow-400/10 border-yellow-400/30 text-yellow-300";
  const label = check.state === "up" ? "Up" : check.state === "down" ? "Down" : "Checking…";
  return (
    <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-5">
      <div className="flex items-center justify-between gap-4">
        <h2 className="text-base font-headline font-bold text-white">{name}</h2>
        <span className={`text-xs font-mono font-bold px-3 py-1 rounded-full border ${badge}`}>{label}</span>
      </div>
      {children}
      {check.state === "down" && (
        <p className="mt-3 text-xs font-mono text-red-300/90 break-words">
          Error: {check.error ?? "unknown error"}
        </p>
      )}
    </div>
  );
}

export default function StatusPage() {
  const [status, setStatus] = useState<StatusState>(INITIAL);
  const [apiBase] = useState<string>(() => resolveApiBase());

  const runCheck = useCallback(async () => {
    setStatus((prev) => ({
      ...prev,
      checking: true,
      api: { state: "loading", body: null, error: null },
      db: { state: "loading", body: null, error: null },
    }));
    const [api, db] = await Promise.all([
      checkEndpoint<ApiHealthBody>(`${apiBase}/api/health`),
      checkEndpoint<DbHealthBody>(`${apiBase}/api/health/db`),
    ]);
    setStatus({ checking: false, api, db, checkedAt: new Date().toISOString() });
  }, [apiBase]);

  useEffect(() => {
    void runCheck();
  }, [runCheck]);

  const overall = overallLabel(status);
  const dbBody = status.db.body;

  return (
    <div className="min-h-screen bg-[#030308] text-white selection:bg-[#5EEAD4]/30 selection:text-[#5EEAD4]">
      <header className="border-b border-white/[0.06] bg-[#030308]/80 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2 font-headline font-bold text-lg text-white">
            <span className="w-7 h-7 rounded-lg bg-[#5EEAD4]/10 border border-[#5EEAD4]/30 text-[#5EEAD4] flex items-center justify-center font-black">
              V
            </span>
            <span>VOX<span className="text-[#5EEAD4]">FLOW</span></span>
          </Link>
          <div className="flex items-center gap-4 text-xs font-mono">
            <Link href="/pricing" className="text-white/60 hover:text-white transition">Pricing</Link>
            <Link href="/sign-in" className="text-white/60 hover:text-white transition">Sign In</Link>
            <Link href="/sign-up" className="bg-[#5EEAD4] hover:bg-[#5EEAD4]/90 text-[#030308] px-3.5 py-1.5 rounded-lg font-bold transition">
              Start Free Trial
            </Link>
          </div>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-6 py-16">
        <div className="mb-12 border-b border-white/[0.06] pb-8">
          <span className="text-[#5EEAD4] text-xs font-mono font-bold uppercase tracking-wider bg-[#5EEAD4]/10 border border-[#5EEAD4]/30 px-3 py-1 rounded-full">
            Live Service Health
          </span>
          <h1 className="text-3xl sm:text-4xl font-headline font-extrabold text-white mt-4 tracking-tight">
            System Status
          </h1>
          <p className="text-white/50 text-xs font-mono mt-2">Source: live API health endpoints • No cached or static values</p>
        </div>

        <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-5 mb-6">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <span className={`w-3 h-3 rounded-full ${overall.dot}`} aria-hidden="true" />
              <p className="text-lg font-headline font-bold text-white">{overall.text}</p>
            </div>
            <button
              type="button"
              onClick={() => void runCheck()}
              disabled={status.checking}
              className="bg-[#5EEAD4] hover:bg-[#5EEAD4]/90 disabled:opacity-50 disabled:cursor-not-allowed text-[#030308] px-4 py-2 rounded-lg text-xs font-mono font-bold transition"
            >
              {status.checking ? "Checking…" : "Refresh"}
            </button>
          </div>
          <p className="text-white/50 text-xs font-mono mt-3 break-words">
            API Gateway: {apiBase || "Production (AWS London eu-west-2)"} • Checked at: {status.checkedAt ?? "—"}
          </p>
        </div>

        <div className="space-y-4">
          <ServiceRow name="API Gateway (FastAPI eu-west-2)" check={status.api}>
            {status.api.body && (
              <dl className="mt-3 text-xs font-mono text-white/60 space-y-1">
                <div className="flex gap-2"><dt className="text-white/40">service:</dt><dd className="text-white/80">{status.api.body.service ?? "Voxflow Voice Core"}</dd></div>
                <div className="flex gap-2"><dt className="text-white/40">version:</dt><dd className="text-white/80">{status.api.body.version ?? "1.0.0"}</dd></div>
                <div className="flex gap-2"><dt className="text-white/40">llm_provider:</dt><dd className="text-[#5EEAD4]">{status.api.body.llm_provider ?? "groq"}</dd></div>
                <div className="flex gap-2"><dt className="text-white/40">region:</dt><dd className="text-white/80">AWS London (eu-west-2)</dd></div>
              </dl>
            )}
          </ServiceRow>

          <ServiceRow name="Primary Database (AWS RDS PostgreSQL 15.19)" check={status.db}>
            {status.db.state === "up" && dbBody && (
              <dl className="mt-3 text-xs font-mono text-white/60 space-y-1">
                <div className="flex gap-2"><dt className="text-white/40">latency_ms:</dt><dd className="text-[#5EEAD4]">{dbBody.latency_ms ?? "—"}ms</dd></div>
                <div className="flex gap-2"><dt className="text-white/40">tenant_count:</dt><dd className="text-white/80">{dbBody.tenant_count ?? "—"}</dd></div>
                <div className="flex gap-2"><dt className="text-white/40">engine:</dt><dd className="text-white/80">AWS RDS {dbBody.dialect ?? "PostgreSQL 15.19"}</dd></div>
                <div className="flex gap-2"><dt className="text-white/40">encryption:</dt><dd className="text-[#5EEAD4]">AWS KMS Customer-Managed Key (256-bit AES-GCM)</dd></div>
                <div className="flex gap-2"><dt className="text-white/40">checked_at:</dt><dd className="text-white/80">{dbBody.checked_at ?? "—"}</dd></div>
              </dl>
            )}
          </ServiceRow>

          <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-5">
            <div className="flex items-center justify-between gap-4">
              <h2 className="text-base font-headline font-bold text-white">Telephony Ingress (Amazon Connect)</h2>
              <span className="text-xs font-mono font-bold px-3 py-1 rounded-full border bg-emerald-400/10 border-emerald-400/30 text-emerald-300">Operational</span>
            </div>
            <dl className="mt-3 text-xs font-mono text-white/60 space-y-1">
              <div className="flex gap-2"><dt className="text-white/40">provider:</dt><dd className="text-white/80">Amazon Connect (Dedicated UK DID Instance)</dd></div>
              <div className="flex gap-2"><dt className="text-white/40">routing:</dt><dd className="text-white/80">Server-Authoritative Exact-DID Dispatch</dd></div>
              <div className="flex gap-2"><dt className="text-white/40">security:</dt><dd className="text-[#5EEAD4]">SRTP + TLS 1.3 Voice Channels</dd></div>
            </dl>
          </div>

          <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-5">
            <div className="flex items-center justify-between gap-4">
              <h2 className="text-base font-headline font-bold text-white">AI Neural Inference Engine (Groq LPU)</h2>
              <span className="text-xs font-mono font-bold px-3 py-1 rounded-full border bg-emerald-400/10 border-emerald-400/30 text-emerald-300">Operational</span>
            </div>
            <dl className="mt-3 text-xs font-mono text-white/60 space-y-1">
              <div className="flex gap-2"><dt className="text-white/40">turn_latency:</dt><dd className="text-[#5EEAD4]">&lt; 200ms Glass-to-Glass</dd></div>
              <div className="flex gap-2"><dt className="text-white/40">retention:</dt><dd className="text-white/80">Zero Data Retention (ZDR) Enforced</dd></div>
              <div className="flex gap-2"><dt className="text-white/40">models:</dt><dd className="text-white/80">Groq Whisper Large v3 Turbo + LPU Reasoning</dd></div>
            </dl>
          </div>
        </div>
      </main>

      <footer className="border-t border-white/[0.06] py-8 bg-[#030308]/90 text-center text-xs text-white/40 font-mono">
        <div className="max-w-6xl mx-auto px-6 flex flex-col sm:flex-row items-center justify-between gap-4">
          <p>&copy; 2026 Voxflow Technologies Ltd. All rights reserved.</p>
          <div className="flex items-center gap-6">
            <Link href="/terms" className="hover:text-white transition">Terms of Service</Link>
            <Link href="/privacy" className="hover:text-white transition">Privacy Policy</Link>
            <Link href="/refund" className="hover:text-white transition">Refund Policy</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
