"use client";

import { useEffect } from "react";

export default function CrispChat() {
  useEffect(() => {
    const websiteId = process.env.NEXT_PUBLIC_CRISP_WEBSITE_ID;
    if (!websiteId || typeof window === "undefined") return;

    // Initialize Crisp global queue
    (window as unknown as { $crisp: unknown[] }).$crisp = [];
    (window as unknown as { CRISP_WEBSITE_ID: string }).CRISP_WEBSITE_ID = websiteId;

    const d = document;
    const s = d.createElement("script");
    s.src = "https://client.crisp.chat/l.js";
    s.async = true;
    d.getElementsByTagName("head")[0].appendChild(s);
  }, []);

  return null;
}
