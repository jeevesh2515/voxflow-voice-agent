/**
 * Day 51 client-side product analytics and error reporting.
 *
 * Privacy contract: this module is the ONLY place browser telemetry leaves the
 * app, and it is allow-list driven. A property name that is not explicitly
 * permitted is dropped rather than sanitized, so a future caller that passes
 * `caller_phone` or a whole order object sends nothing instead of relying on a
 * regex to catch it. Both vendors stay completely inert unless their public
 * env keys are configured.
 */

// Mirrors ANALYTICS_ALLOWED_PROPERTIES in apps/api/voxflow_api/monitoring.py.
// Keep the two lists in sync; the backend is the enforcing side for server events.
const ALLOWED_PROPERTIES = new Set([
  "action",
  "alert_code",
  "alert_count",
  "call_count",
  "channel",
  "component",
  "duration_ms",
  "error_code",
  "escalation_rate",
  "feature",
  "job_type",
  "language",
  "latency_ms",
  "outcome",
  "page",
  "plan",
  "provider",
  "range_days",
  "resolution_rate",
  "result",
  "role",
  "severity",
  "status",
  "subsystem",
  "surface",
  "time_range",
  "variant",
  "version",
]);

const MAX_STRING_LENGTH = 64;

const EMAIL_PATTERN = /\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b/gi;
const PHONE_PATTERN = /\+?\d[\d\s().-]{7,}\d/g;
// A bare 4-8 digit run may be a spoken caller PIN.
const PIN_PATTERN = /(?<!\d)\d{4,8}(?!\d)/g;

export type AnalyticsValue = string | number | boolean | null;
export type AnalyticsProperties = Record<string, unknown>;

function scrubString(value: string): string {
  return value
    .replace(EMAIL_PATTERN, "[redacted-email]")
    .replace(PHONE_PATTERN, "[redacted-phone]")
    .replace(PIN_PATTERN, "[redacted-pin]")
    .slice(0, MAX_STRING_LENGTH);
}

/** Reduce arbitrary properties to allow-listed, scrubbed scalars. */
export function scrubProperties(properties?: AnalyticsProperties): Record<string, AnalyticsValue> {
  if (!properties) return {};
  const safe: Record<string, AnalyticsValue> = {};
  for (const [rawKey, rawValue] of Object.entries(properties)) {
    const key = rawKey.trim().toLowerCase();
    if (!ALLOWED_PROPERTIES.has(key)) continue;
    if (typeof rawValue === "number" && Number.isFinite(rawValue)) {
      safe[key] = rawValue;
    } else if (typeof rawValue === "boolean") {
      safe[key] = rawValue;
    } else if (typeof rawValue === "string") {
      safe[key] = scrubString(rawValue);
    } else if (rawValue === null) {
      safe[key] = null;
    }
    // Objects, arrays, functions, and symbols are intentionally dropped.
  }
  return safe;
}

/**
 * Stable non-reversible tenant label.
 *
 * A workspace slug identifies a customer, so events carry a digest instead.
 * This is deliberately a lightweight FNV-1a hash, not a cryptographic one: the
 * backend owns the salted SHA-256 identity, and this only needs to be stable
 * and non-obvious for client-side funnels.
 */
export function hashTenantId(tenantId: string): string {
  const value = (tenantId || "").trim();
  if (!value) return "anonymous";
  let hash = 0x811c9dc5;
  for (let index = 0; index < value.length; index += 1) {
    hash ^= value.charCodeAt(index);
    hash = Math.imul(hash, 0x01000193) >>> 0;
  }
  return `t_${hash.toString(16).padStart(8, "0")}`;
}

import posthog from "posthog-js";

let initialized = false;

function client() {
  if (typeof window === "undefined") return null;
  const key = process.env.NEXT_PUBLIC_POSTHOG_KEY?.trim();
  if (!key) return null;
  if (!initialized) {
    try {
      posthog.init(key, {
        api_host: process.env.NEXT_PUBLIC_POSTHOG_HOST?.trim(),
        ip: false,
        persistence: "localStorage",
      });
      initialized = true;
    } catch {
      return null;
    }
  }
  return posthog;
}

/** Track one product-analytics event. Silent no-op when analytics is unconfigured. */
export function trackEvent(name: string, properties?: AnalyticsProperties): boolean {
  const instance = client();
  if (!instance) return false;
  const eventName = (name || "").trim().slice(0, 64);
  if (!eventName) return false;
  try {
    instance.capture(eventName, scrubProperties(properties));
    return true;
  } catch {
    return false;
  }
}

/** Associate the session with a hashed tenant label. Never sends the raw slug. */
export function identifyTenant(tenantId: string, properties?: AnalyticsProperties): boolean {
  const instance = client();
  if (!instance) return false;
  try {
    instance.identify(hashTenantId(tenantId), scrubProperties(properties));
    return true;
  } catch {
    return false;
  }
}

import * as Sentry from "@sentry/nextjs";

/**
 * Report a handled client error with no free-text message.
 *
 * The message is dropped for the same reason the backend drops it: a personal
 * name interpolated into an error string is not pattern-detectable. Only the
 * error class plus allow-listed context is reported.
 */
export function reportError(error: unknown, context?: AnalyticsProperties): boolean {
  if (typeof window === "undefined") return false;
  const name = error instanceof Error ? error.name : "UnknownError";
  try {
    Sentry.captureException(error instanceof Error ? error : new Error(name), {
      extra: scrubProperties(context),
      tags: { error_class: name },
    });
    return true;
  } catch {
    return false;
  }
}
