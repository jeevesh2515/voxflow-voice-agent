"use client";

import { useEffect, useRef, useState } from "react";
import Script from "next/script";

type TurnstileApi = {
  render: (container: HTMLElement, options: Record<string, unknown>) => string;
  reset: (widgetId: string) => void;
  remove: (widgetId: string) => void;
};

declare global {
  interface Window { turnstile?: TurnstileApi; }
}

type Props = {
  action: "sign_in" | "sign_up";
  onToken: (token: string | null) => void;
  resetCounter?: number;
};

export function turnstileEnabled() {
  return Boolean(process.env.NEXT_PUBLIC_TURNSTILE_SITE_KEY);
}

export default function TurnstileWidget({ action, onToken, resetCounter = 0 }: Props) {
  const container = useRef<HTMLDivElement | null>(null);
  const widgetId = useRef<string | null>(null);
  const [scriptLoaded, setScriptLoaded] = useState(false);
  const siteKey = process.env.NEXT_PUBLIC_TURNSTILE_SITE_KEY;

  useEffect(() => {
    if (!siteKey || !scriptLoaded || !container.current || !window.turnstile || widgetId.current) return;
    widgetId.current = window.turnstile.render(container.current, {
      sitekey: siteKey,
      action,
      theme: "dark",
      size: "flexible",
      callback: (token: string) => onToken(token),
      "expired-callback": () => onToken(null),
      "error-callback": () => onToken(null),
    });
    return () => {
      if (widgetId.current && window.turnstile) window.turnstile.remove(widgetId.current);
      widgetId.current = null;
    };
  }, [action, onToken, scriptLoaded, siteKey]);

  useEffect(() => {
    if (!resetCounter || !widgetId.current || !window.turnstile) return;
    window.turnstile.reset(widgetId.current);
    onToken(null);
  }, [onToken, resetCounter]);

  if (!siteKey) return null;
  return (
    <div className="space-y-2">
      <Script src="https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit" strategy="afterInteractive" onLoad={() => setScriptLoaded(true)} />
      <div ref={container} className="min-h-[65px]" />
      <p className="text-[10px] text-[#94a3b8]">Verification is checked server-side before this form submits.</p>
    </div>
  );
}
