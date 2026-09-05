import { NextResponse } from "next/server";

export async function GET() {
  const posthogKey = process.env.NEXT_PUBLIC_POSTHOG_KEY?.trim();
  const posthogHost = process.env.NEXT_PUBLIC_POSTHOG_HOST?.trim() || "https://eu.i.posthog.com";

  if (!posthogKey) {
    return NextResponse.json({
      ok: false,
      configured: false,
      message: "PostHog API key (NEXT_PUBLIC_POSTHOG_KEY) is not configured.",
    }, { status: 400 });
  }

  try {
    const payload = {
      api_key: posthogKey,
      event: "posthog_connection_verified",
      properties: {
        distinct_id: "voxflow-test-probe",
        service: "voxflow-web",
        timestamp: new Date().toISOString(),
      },
    };

    const res = await fetch(`${posthogHost.replace(/\/+$/, "")}/capture/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const body = await res.json().catch(() => null);

    return NextResponse.json({
      ok: res.ok,
      configured: true,
      host: posthogHost,
      posthog_status: res.status,
      response: body,
      message: "PostHog connection successfully verified and synthetic event captured.",
    });
  } catch (err) {
    return NextResponse.json({
      ok: false,
      configured: true,
      error: err instanceof Error ? err.message : String(err),
    }, { status: 500 });
  }
}
