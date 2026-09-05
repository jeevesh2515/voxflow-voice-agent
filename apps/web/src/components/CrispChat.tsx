"use client";

import { useEffect } from "react";

declare global {
  interface Window {
    $crisp?: unknown[];
    CRISP_WEBSITE_ID?: string;
  }
}

export function openCrispSupport(userEmail?: string, userName?: string) {
  if (typeof window === "undefined") return;
  if (!window.$crisp) {
    window.$crisp = [];
  }
  if (userEmail) {
    window.$crisp.push(["set", "user:email", [userEmail]]);
  }
  if (userName) {
    window.$crisp.push(["set", "user:nickname", [userName]]);
  }
  window.$crisp.push(["do", "chat:open"]);
}

export default function CrispChat() {
  useEffect(() => {
    const websiteId = process.env.NEXT_PUBLIC_CRISP_WEBSITE_ID;
    if (!websiteId || typeof window === "undefined") return;

    window.$crisp = [];
    window.CRISP_WEBSITE_ID = websiteId;

    const d = document;
    const s = d.createElement("script");
    s.src = "https://client.crisp.chat/l.js";
    s.async = true;
    d.getElementsByTagName("head")[0].appendChild(s);
  }, []);

  return null;
}
