export type FaqEntry = { q: string; a: string };

export const faq: FaqEntry[] = [
  {
    q: "Can we port our existing DID numbers?",
    a: "Yes. We support number porting from most UK providers. Keep your current numbers; callers notice nothing different. Typical port time: 5–10 working days.",
  },
  {
    q: "Does it sync with Google Sheets?",
    a: "Yes. Call outcomes, bookings, and customer details can push straight to a Google Sheet via Zapier or our API. No manual re-entry.",
  },
  {
    q: "Where is call data stored? GDPR?",
    a: "Audio and transcripts stay in eu-west-2 (London). We do not train on your calls. Data stays yours — delete anytime.",
  },
  {
    q: "What counts as a billable minute?",
    a: "Only answered call duration. Ringing, failed calls, and voicemail are free. You pay for real conversations, not dead air.",
  },
  {
    q: "What's the difference between IVR and operator switch?",
    a: "IVR gives callers a fixed menu tree. Operator switch routes dynamically based on intent — more flexible, higher resolution rate.",
  },
  {
    q: "When does a call go to a human?",
    a: "On-demand. Set triggers: escalated complaints, complex bookings, explicit 'speak to a person' request. You choose the handoff rules.",
  },
  {
    q: "Does it handle Hindi or other languages?",
    a: "Yes. Hindi, Urdu, Punjabi, and 10+ other languages are live. Caller language is detected automatically.",
  },
  {
    q: "Can we start with one phone number?",
    a: "Yes. Start with one number, one workflow. Scale up whenever you want — no lock-in, no minimum commitment.",
  },
];
