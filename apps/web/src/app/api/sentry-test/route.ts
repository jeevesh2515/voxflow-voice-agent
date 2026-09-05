import { NextResponse } from "next/server";
import * as Sentry from "@sentry/nextjs";

export async function GET() {
  try {
    throw new Error("VoxFlow Web Phase 3 Sentry Verification Test");
  } catch (err) {
    const eventId = Sentry.captureException(err);
    return NextResponse.json({
      ok: true,
      service: "voxflow-web",
      message: "Client/Next.js Sentry verification test triggered successfully.",
      sentry_event_id: eventId,
      configured: Boolean(process.env.NEXT_PUBLIC_SENTRY_DSN || process.env.SENTRY_DSN),
    });
  }
}
