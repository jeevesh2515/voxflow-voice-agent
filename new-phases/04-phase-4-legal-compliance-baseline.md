# Phase 4: Legal & Compliance Baseline

## Objective

The legal documents and in-product consent flows required before you can
lawfully bill a customer and record their calls. This phase did not exist in
the original gap assessment despite the product already marketing "UK GDPR
Default" — it is being added because it is a real blocker, not optional
polish.

## Prerequisites

Phase 3 Definition of Done met (email infrastructure exists to deliver
policy-acceptance confirmations, etc.). Note: Phase 0 already published a
free-template ToS/Privacy Policy and implemented the call-recording
disclosure — this phase is where those get a real solicitor review and the
DPA gets built, before any real (non-demo) contract is signed. It does not
require Phase 1's funded AWS migration to be done first, but it does need to
happen before real money changes hands, regardless of funding status.

## Tools required

- A solicitor or a template service (Termly, Ironclad's free templates) for
  a first pass — **a real legal review is required before this phase's
  Definition of Done can be marked complete for a paying customer.** AI- or
  template-drafted text alone is not sufficient to ship.

## Working steps

1. Draft Terms of Service and Privacy Policy, starting from a template if
   useful, then route to a solicitor for review.
2. Draft a Data Processing Agreement (DPA) template — enterprise logistics
   and FMCG customers will ask for this before signing, and having it ready
   shortens sales cycles rather than blocking them.
3. Implement a spoken (or DTMF) call-recording disclosure at the start of
   every call flow through AWS Connect, satisfying UK PECR requirements for
   recorded lines. This is a call-flow code change, not just a policy
   document — verify it by listening to an actual test call.
4. Define a data retention policy for call recordings and transcripts, and
   implement automatic deletion after the defined window in code — not just
   documented, actually enforced and testable.
5. Publish a subprocessor list (AWS, Groq, Stripe, Resend, and any others in
   the stack) at a stable URL — enterprise procurement will ask for this.
6. Prepare (but don't need to fully build yet) the cookie-consent
   requirement for the marketing site — full implementation happens in
   Phase 5, but the policy content this depends on is finalized here.

## Definition of Done

- [ ] ToS and Privacy Policy published, and reviewed by a solicitor —
      confirmed, not assumed
- [ ] DPA template ready to send to a prospect on request
- [ ] Every call flow plays or otherwise delivers a recorded-line disclosure
      before recording starts, verified on an actual test call
- [ ] Data retention window is enforced in code, with automatic deletion
      verified in a test run
- [ ] Subprocessor list published at a stable, linkable URL
- [ ] Full existing test/eval suite still passes at 100%

## Explicitly out of scope for this phase

- SOC 2 — Phase 6; that's a compliance framework audit, distinct from having
  baseline legal documents in place, and you need this phase regardless of
  whether SOC 2 is ever pursued
- Cookie consent banner implementation — Phase 5
