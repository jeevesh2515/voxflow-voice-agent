# PostHog Self-driving setup report

## Summary

PostHog Self-driving is configured for VoxFlow. Session Replay, Error Tracking, and Support were enabled; health, error, support, GitHub Issues, and dormant Sentry signal sources were configured. The web SDK no longer overrides Replay or automatic capture, and findings should start appearing in the [Self-driving inbox](https://eu.posthog.com/project/267182/inbox) within about 30 minutes.

## AI data processing

Approved. Organization-level AI data processing approval was confirmed by the setup gate before this run.

## GitHub

GitHub was already connected through the PostHog GitHub App. This setup connected the `jeevesh2515/voxflow-voice-agent` GitHub Issues warehouse source (`01a07362-d687-0000-af64-045df34b6929`); its initial issues sync has started. Only the `issues` table is enabled for sync, which is the table used by the responder; additional GitHub tables can be enabled in PostHog later if needed.

## Products enabled

| Product | Result | Notes |
| --- | --- | --- |
| Session Replay | enabled | Browser initialization was edited to remove `disable_session_recording: true`. |
| Error Tracking | enabled | No client `capture_exceptions: false` override was present. |
| Support / Conversations | enabled | An inbound email, inbox, or Slack channel must still be connected before tickets exist. |

## Signal sources

| Signal source | Action | Notes |
| --- | --- | --- |
| `signals_scout` / `cross_source_issue` | enabled by default | No opt-out row is required; scout findings can reach the inbox. |
| `health_checks` / `health_issue` | enabled | Setup and instrumentation health findings are actionable. |
| `error_tracking` / `issue_created` | enabled | New exception issues reach the inbox. |
| `error_tracking` / `issue_reopened` | enabled | Reopened exception issues reach the inbox. |
| `error_tracking` / `issue_spiking` | enabled | Exception-volume spikes reach the inbox. |
| `conversations` / `ticket` | enabled | Dormant until an inbound Support channel is connected. |
| `github` / `issue` | enabled | Backed by the GitHub Issues warehouse source created in this setup. |
| `sentry` / `issue` | enabled (dormant) | Selected, but no Sentry warehouse source was connected. |
| `session_replay` / `session_analysis_cluster` | skipped | Retired route; Replay Vision scanners provide replay coverage. |

## Connected tools

| Tool | Result |
| --- | --- |
| GitHub Issues | Connected by this setup; source `01a07362-d687-0000-af64-045df34b6929`, first sync started. |
| Sentry | Selected but no source detected; the responder is enabled and dormant until a Sentry warehouse source is connected. |
| Linear, Jira, Zendesk, and other catalog tools | Not used in this setup. |

## Scout troop

Five built-in scouts are active, each on the server default daily cadence. The verified budget is **100 runs/day**, with **0 used today** and **100 remaining**. The project announcement states: “Scouts are in early access. Each project gets up to 100 scout runs a day. Contact team-self-driving@posthog.com if you need more.”

### Active scouts

| Scout | Why active |
| --- | --- |
| `general` | Cross-product correlations and surfaces without a specialist. |
| `product-analytics` | Product-flow, conversion, retention, and engagement monitoring. |
| `web-analytics` | Browser traffic, attribution, landing-page, and session-volume health. |
| `revenue-analytics` | Stripe subscription and revenue-capture health. |
| `health-checks` | Prioritizes actionable PostHog setup health issues. |

### Disabled scouts

| Scout | Reason |
| --- | --- |
| `ai-observability` | No verified LLM Analytics traces. |
| `anomaly-detection` | No established saved insights or dashboards to monitor yet. |
| `apm` | No verified PostHog APM or OpenTelemetry surface. |
| `conversations` | Support channel is not connected yet. |
| `csp-violations` | No configured CSP reporting evidence. |
| `customer-analytics` | No verified PostHog Accounts analytics surface. |
| `data-pipelines` | No verified CDP or batch-export pipeline use. |
| `data-warehouse` | GitHub Issues sync is new; enable later if warehouse monitoring becomes needed. |
| `error-tracking` | Covered by the native Error Tracking responders. |
| `experiments` | No active A/B experiments found. |
| `feature-flags` | No active feature-flag usage found. |
| `inbox-validation` | Fresh inbox setup has no resolved fixes to validate yet. |
| `insight-alerts` | No configured PostHog insight alerts found. |
| `logs` | No verified PostHog Logs product use. |
| `mcp-tool-calls` | Not a product monitoring priority. |
| `observability-gaps` | Generic coverage is supplied by the focused product and health scouts initially. |
| `replay-vision` | Fresh Replay Vision scanners have no observations to aggregate yet. |
| `session-replay` | Covered by the Replay Vision scanners below. |
| `skills-store` | Not a product monitoring priority. |
| `surveys` | No surveys found. |
| `tasks` | No verified PostHog Tasks use. |
| `web-vitals` | No evidence of captured Core Web Vitals yet. |

## Custom scouts

No custom scouts were created. Two candidates were proposed and not accepted: a reviewer for high-impact inbound voice-routing and caller-verification changes, and a call-resolution/escalation health monitor. The latter needs core operational call outcomes to be captured in PostHog before it can observe reliable live behavior. The built-in `health-checks` scout covers general configuration health; the `revenue-analytics` scout covers billing; and the native Error Tracking and Replay Vision routes cover exceptions and visual replay issues.

If a future custom scout becomes noisy, set its `emit` config to `false` in PostHog to switch it to dry-run mode.

## Replay Vision scanners

A scanner is an LLM that watches individual session recordings on a schedule and pushes meaningful observations to the Self-driving inbox. It is the only component in this setup that consumes Replay Vision quota. Scanner findings have half weight and need corroboration before they are promoted into a report.

| Brief | Scanner | Status | Scope | Sampling | Estimate |
| --- | --- | --- | --- | --- | --- |
| Breakage monitor | `VoxFlow onboarding breakage` | created | Sessions on `/onboarding`, the workspace setup flow that configures an agent, tests it, and launches the operations dashboard. | 0.5 | 0 observations / 0 credits monthly at current traffic. |
| Frustration monitor | `VoxFlow operator frustration` | created | Sessions containing `$rageclick`; intentionally no URL scope so it complements the onboarding monitor. | 1.0 | 0 observations / 0 credits monthly at current traffic. |

The organization has 2,500 Replay Vision credits remaining in the current period and has used none. No recordings were available during setup, so both scanners are armed and will start working as recordings arrive.

## Files modified or created

| File | Change |
| --- | --- |
| `.env.local` | Set the configured PostHog public key and EU ingestion host. |
| `src/app/providers.tsx` | Removed browser SDK overrides that disabled autocapture and Session Replay; the host is read from the environment. |
| `src/lib/observability.ts` | Removed browser SDK overrides that disabled autocapture and Session Replay; the host is read from the environment. |
| `posthog-self-driving-report.md` | Created this setup report. |

`npm run build` completed successfully after the SDK changes.

## Follow-ups

- [ ] Connect an inbound Support channel (email, inbox, or Slack) to activate Support ticket findings.
- [ ] Connect Sentry securely in PostHog to activate the already-enabled, currently dormant Sentry responder: [new warehouse source](https://eu.posthog.com/project/267182/pipeline/new/source).
- [ ] Send privacy-safe operational call outcomes, resolutions, escalations, and latency telemetry to PostHog before enabling the proposed call-resolution custom scout.
- [ ] Consider enabling the `data-warehouse` scout after the new GitHub Issues import has a sync history.

## What happens next

The scout coordinator picks up fresh configuration within about 30 minutes. Scout runs consume the daily budget, observations cluster into reports in the [Self-driving inbox](https://eu.posthog.com/project/267182/inbox), and immediately actionable findings can start coding tasks.
