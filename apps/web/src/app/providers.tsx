"use client";

import posthog from "posthog-js";
import { PostHogProvider as PHProvider } from "posthog-js/react";
import { useEffect } from "react";

export function PostHogProvider({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    const posthogKey = process.env.NEXT_PUBLIC_POSTHOG_KEY?.trim();
    if (posthogKey) {
      posthog.init(posthogKey, {
        api_host: process.env.NEXT_PUBLIC_POSTHOG_HOST?.trim() || "https://us.i.posthog.com",
        person_profiles: "identified_only",
        capture_pageview: false,
        autocapture: false,
        disable_session_recording: true,
      });
    }
  }, []);

  return <PHProvider client={posthog}>{children}</PHProvider>;
}
