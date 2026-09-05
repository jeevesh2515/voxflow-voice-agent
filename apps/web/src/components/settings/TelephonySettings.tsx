"use client";

import { useEffect, useMemo, useState, type FormEvent } from "react";
import useSWR from "swr";
import {
  AlertTriangle,
  CheckCircle2,
  CircleOff,
  Globe2,
  KeyRound,
  Lock,
  Pencil,
  PhoneCall,
  Plus,
  Radio,
  RefreshCw,
  ShieldCheck,
  Trash2,
  X,
} from "lucide-react";
import { api } from "@/lib/api";
import { useTenant } from "@/lib/tenant-context";
import type {
  CallerVerificationMode,
  TelephonyLanguage,
  TelephonyPhoneNumber,
  TelephonyPhoneNumberInput,
  TelephonyProvider,
  TelephonySettings as TelephonySettingsResponse,
  VerificationContact,
} from "@/lib/types";

// Amazon Connect is the only inbound telephony provider currently wired to a
// live route (voxflow_api/routes/connect.py). The API only accepts "connect"
// when creating or updating a line, so no other option is offered here —
// showing one would let an owner create a mapping that can never ring.
const PROVIDERS: ReadonlyArray<{ value: TelephonyProvider; label: string }> = [
  { value: "connect", label: "Amazon Connect" },
];

const VERIFICATION_MODES: ReadonlyArray<{ value: CallerVerificationMode; label: string; detail: string }> = [
  { value: "enhanced", label: "Enhanced · PIN required", detail: "Challenge matched contacts with a PIN before protected actions." },
  { value: "standard", label: "Standard verification", detail: "Use the standard caller identity and knowledge-factor policy." },
];

const LANGUAGES: ReadonlyArray<{ value: TelephonyLanguage; label: string }> = [
  { value: "tenant_default", label: "Workspace default" },
  { value: "en", label: "English (UK / Global)" },
];

const EMPTY_PHONE_FORM: TelephonyPhoneNumberInput = {
  phone_number: "",
  label: "",
  provider: "connect",
  verification_mode: "enhanced",
  route_language: "tenant_default",
  active: true,
};

const controlClass =
  "w-full rounded-xl border border-[#302840] bg-[#10101b] px-3.5 py-2.5 text-sm text-[#e8e0f0] outline-none transition placeholder:text-[#655d70] focus:border-[#00ffcc]/70 focus:ring-2 focus:ring-[#00ffcc]/10 disabled:cursor-not-allowed disabled:opacity-50";
const secondaryButtonClass =
  "inline-flex items-center justify-center gap-2 rounded-xl border border-[#302840] bg-[#181826] px-3.5 py-2 text-xs font-semibold text-[#c9c1d3] transition hover:border-[#00ffcc]/40 hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#00ffcc]/50 disabled:cursor-not-allowed disabled:opacity-40";

function providerLabel(provider: TelephonyProvider): string {
  return PROVIDERS.find((option) => option.value === provider)?.label ?? provider;
}

function verificationLabel(mode: CallerVerificationMode): string {
  return VERIFICATION_MODES.find((option) => option.value === mode)?.label ?? mode;
}

function languageLabel(language: TelephonyLanguage): string {
  return LANGUAGES.find((option) => option.value === language)?.label ?? language;
}

function formatTimestamp(value: string | null | undefined): string {
  if (!value) return "Not yet updated";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Time unavailable";
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

function roleLabel(role: string, demoMode: boolean): string {
  if (demoMode) return "Demo · read only";
  return `${role.charAt(0).toUpperCase()}${role.slice(1)}${role === "owner" ? " · full access" : " · read only"}`;
}

function PhoneNumberEditor({
  mode,
  value,
  saving,
  error,
  onChange,
  onCancel,
  onSubmit,
}: {
  mode: "create" | "edit";
  value: TelephonyPhoneNumberInput;
  saving: boolean;
  error: string | null;
  onChange: (value: TelephonyPhoneNumberInput) => void;
  onCancel: () => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
}) {
  const title = mode === "create" ? "Add inbound line" : "Edit inbound line";
  return (
    <form
      id="phone-number-editor"
      onSubmit={onSubmit}
      aria-busy={saving}
      className="rounded-2xl border border-[#00ffcc]/25 bg-[linear-gradient(145deg,rgba(0,255,204,0.06),rgba(20,20,34,0.85)_45%)] p-5 sm:p-6"
    >
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-[10px] font-mono uppercase tracking-[0.2em] text-[#00ffcc]">Owner configuration</p>
          <h3 className="mt-1 text-base font-bold text-white">{title}</h3>
          <p className="mt-1 text-xs leading-5 text-[#94a3b8]">
            Every destination number maps to this workspace explicitly. Use E.164 format, including the country code.
          </p>
        </div>
        <button type="button" onClick={onCancel} className={secondaryButtonClass} aria-label={`Close ${title.toLowerCase()}`}>
          <X size={15} />
          <span className="hidden sm:inline">Cancel</span>
        </button>
      </div>

      <div className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <label className="space-y-1.5 sm:col-span-1">
          <span className="text-xs font-medium text-[#c9c1d3]">Phone number</span>
          <input
            type="tel"
            inputMode="tel"
            autoComplete="tel"
            required
            disabled={mode === "edit"}
            value={value.phone_number}
            onChange={(event) => onChange({ ...value, phone_number: event.target.value })}
            placeholder="+442079460123"
            aria-describedby="phone-number-hint"
            className={controlClass}
          />
          <span id="phone-number-hint" className="block text-[10px] text-[#756d80]">{mode === "edit" ? "DID identity is immutable; add a new line to change the number." : "8–15 digits after a leading +"}</span>
        </label>

        <label className="space-y-1.5 sm:col-span-1 lg:col-span-2">
          <span className="text-xs font-medium text-[#c9c1d3]">Line label</span>
          <input
            type="text"
            required
            maxLength={80}
            value={value.label}
            onChange={(event) => onChange({ ...value, label: event.target.value })}
            placeholder="London support line"
            className={controlClass}
          />
        </label>

        <label className="space-y-1.5">
          <span className="text-xs font-medium text-[#c9c1d3]">Provider</span>
          <select
            value={value.provider}
            onChange={(event) => onChange({ ...value, provider: event.target.value as TelephonyProvider })}
            className={controlClass}
            disabled
          >
            {PROVIDERS.map((provider) => <option key={provider.value} value={provider.value}>{provider.label}</option>)}
          </select>
          <span className="block text-[10px] text-[#756d80]">Amazon Connect is the only inbound provider currently supported.</span>
        </label>

        <label className="space-y-1.5">
          <span className="text-xs font-medium text-[#c9c1d3]">Caller verification</span>
          <select
            value={value.verification_mode}
            onChange={(event) => onChange({ ...value, verification_mode: event.target.value as CallerVerificationMode })}
            className={controlClass}
          >
            {VERIFICATION_MODES.map((modeOption) => <option key={modeOption.value} value={modeOption.value}>{modeOption.label}</option>)}
          </select>
        </label>

        <label className="space-y-1.5">
          <span className="text-xs font-medium text-[#c9c1d3]">Default language</span>
          <select
            value={value.route_language}
            onChange={(event) => onChange({ ...value, route_language: event.target.value as TelephonyLanguage })}
            className={controlClass}
          >
            {LANGUAGES.map((language) => <option key={language.value} value={language.value}>{language.label}</option>)}
          </select>
        </label>
      </div>

      <label className="mt-4 flex w-fit items-center gap-3 rounded-xl border border-[#302840]/70 bg-[#10101b]/70 px-3.5 py-2.5">
        <input
          type="checkbox"
          checked={value.active}
          onChange={(event) => onChange({ ...value, active: event.target.checked })}
          className="h-4 w-4 accent-[#00ffcc]"
        />
        <span>
          <span className="block text-xs font-semibold text-[#e8e0f0]">Active routing</span>
          <span className="block text-[10px] text-[#81798c]">Inactive mappings never receive tenant context.</span>
        </span>
      </label>

      {error && <p role="alert" className="mt-4 rounded-xl border border-[#ff2d78]/35 bg-[#ff2d78]/10 px-3.5 py-3 text-xs text-[#fecdd3]">{error}</p>}

      <div className="mt-5 flex flex-wrap items-center gap-3">
        <button
          type="submit"
          disabled={saving}
          className="inline-flex items-center justify-center gap-2 rounded-xl bg-[#00ffcc] px-4 py-2.5 text-sm font-bold text-[#061313] transition hover:shadow-[0_0_18px_rgba(0,255,204,0.22)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#00ffcc]/60 disabled:cursor-wait disabled:opacity-50"
        >
          {saving ? <RefreshCw size={15} className="animate-spin" /> : <CheckCircle2 size={15} />}
          {saving ? "Saving…" : mode === "create" ? "Add line" : "Save mapping"}
        </button>
        <p className="text-[10px] text-[#81798c]">Changes affect future inbound routing only.</p>
      </div>
    </form>
  );
}

function PhoneLineCard({
  line,
  canManage,
  confirming,
  busy,
  onEdit,
  onRequestDeactivate,
  onCancelDeactivate,
  onConfirmDeactivate,
}: {
  line: TelephonyPhoneNumber;
  canManage: boolean;
  confirming: boolean;
  busy: boolean;
  onEdit: () => void;
  onRequestDeactivate: () => void;
  onCancelDeactivate: () => void;
  onConfirmDeactivate: () => void;
}) {
  return (
    <article className={`rounded-2xl border p-4 sm:p-5 ${line.active ? "border-[#302840]/80 bg-[#11111d]/75" : "border-[#302840]/50 bg-[#0d0d16]/60 opacity-80"}`}>
      <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="font-mono text-sm font-bold text-white sm:text-base">{line.phone_number}</h3>
            <span className={`rounded-full border px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider ${line.active ? "border-[#00ffcc]/30 bg-[#00ffcc]/10 text-[#00ffcc]" : "border-[#64748b]/30 bg-[#64748b]/10 text-[#94a3b8]"}`}>
              {line.active ? "Active" : "Inactive"}
            </span>
            {line.verification_mode === "enhanced" && (
              <span className="rounded-full border border-[#ffe04a]/25 bg-[#ffe04a]/10 px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider text-[#ffe04a]">PIN protected</span>
            )}
          </div>
          <p className="mt-1 text-sm text-[#c9c1d3]">{line.label}</p>
        </div>

        <div className="flex shrink-0 flex-wrap gap-2">
          <button type="button" onClick={onEdit} disabled={!canManage || busy} className={secondaryButtonClass} title={canManage ? "Edit this mapping" : "Only a workspace owner can edit mappings"}>
            <Pencil size={13} /> Edit
          </button>
          {line.active && !confirming && (
            <button
              type="button"
              onClick={onRequestDeactivate}
              disabled={!canManage || busy}
              className="inline-flex items-center justify-center gap-2 rounded-xl border border-[#ff2d78]/35 bg-[#ff2d78]/5 px-3.5 py-2 text-xs font-semibold text-[#ff9bbd] transition hover:bg-[#ff2d78]/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#ff2d78]/50 disabled:cursor-not-allowed disabled:opacity-40"
              title={canManage ? "Deactivate this mapping" : "Only a workspace owner can deactivate mappings"}
            >
              <Trash2 size={13} /> Deactivate
            </button>
          )}
        </div>
      </div>

      <dl className="mt-4 grid gap-3 border-t border-[#28283c]/70 pt-4 sm:grid-cols-2 lg:grid-cols-4">
        <div><dt className="text-[9px] font-mono uppercase tracking-wider text-[#756d80]">Provider</dt><dd className="mt-1 text-xs text-[#c9c1d3]">{providerLabel(line.provider)}</dd></div>
        <div><dt className="text-[9px] font-mono uppercase tracking-wider text-[#756d80]">Verification</dt><dd className="mt-1 text-xs text-[#c9c1d3]">{verificationLabel(line.verification_mode)}</dd></div>
        <div><dt className="text-[9px] font-mono uppercase tracking-wider text-[#756d80]">Language</dt><dd className="mt-1 text-xs text-[#c9c1d3]">{languageLabel(line.route_language)}</dd></div>
        <div><dt className="text-[9px] font-mono uppercase tracking-wider text-[#756d80]">Last changed</dt><dd className="mt-1 text-xs text-[#c9c1d3]">{formatTimestamp(line.updated_at)}</dd></div>
      </dl>

      {confirming && (
        <div role="group" aria-label={`Confirm deactivation of ${line.phone_number}`} className="mt-4 flex flex-col gap-3 rounded-xl border border-[#ff2d78]/30 bg-[#ff2d78]/10 p-3 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-xs leading-5 text-[#fecdd3]">Deactivate this DID? New calls to it will be rejected instead of falling back to another workspace.</p>
          <div className="flex shrink-0 gap-2">
            <button type="button" onClick={onCancelDeactivate} disabled={busy} className={secondaryButtonClass}>Keep active</button>
            <button type="button" onClick={onConfirmDeactivate} disabled={busy} className="inline-flex items-center gap-2 rounded-xl bg-[#ff2d78] px-3.5 py-2 text-xs font-bold text-white disabled:cursor-wait disabled:opacity-50">
              {busy && <RefreshCw size={13} className="animate-spin" />}
              Confirm
            </button>
          </div>
        </div>
      )}
    </article>
  );
}

function VerificationPanel({
  contacts,
  selectedId,
  canManage,
  saving,
  onSelect,
  onSaved,
}: {
  contacts: VerificationContact[];
  selectedId: string;
  canManage: boolean;
  saving: boolean;
  onSelect: (supplierId: string) => void;
  onSaved: (pin: string, confirmPin: string) => Promise<void>;
}) {
  const [pin, setPin] = useState("");
  const [confirmPin, setConfirmPin] = useState("");
  const [error, setError] = useState<string | null>(null);
  const selectedContact = contacts.find((contact) => contact.supplier_id === selectedId) ?? null;

  useEffect(() => {
    setPin("");
    setConfirmPin("");
    setError(null);
  }, [selectedId]);

  async function submitPin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    if (!/^[0-9]{4,8}$/.test(pin)) {
      setError("PIN must contain 4–8 digits.");
      return;
    }
    if (pin !== confirmPin) {
      setError("PIN confirmation does not match.");
      return;
    }
    try {
      await onSaved(pin, confirmPin);
      setPin("");
      setConfirmPin("");
    } catch {
      setPin("");
      setConfirmPin("");
      setError("The PIN could not be updated. No secret value was retained in this form.");
    }
  }

  return (
    <section className="rounded-2xl border border-[#302840]/70 bg-[#141422]/55 overflow-hidden">
      <div className="border-b border-[#302840]/50 bg-[#0f0f1a]/70 px-5 py-4 sm:px-6">
        <div className="flex items-center gap-3">
          <span className="rounded-xl border border-[#ffe04a]/25 bg-[#ffe04a]/10 p-2 text-[#ffe04a]"><KeyRound size={18} /></span>
          <div>
            <h2 className="text-base font-bold text-white">Caller verification PIN</h2>
            <p className="mt-0.5 text-xs text-[#94a3b8]">Set or reset a contact secret without exposing the stored PIN or hash.</p>
          </div>
        </div>
      </div>

      <div className="p-5 sm:p-6">
        {contacts.length === 0 ? (
          <div className="rounded-xl border border-dashed border-[#302840] bg-[#10101b]/60 px-4 py-8 text-center">
            <CircleOff size={22} className="mx-auto text-[#655d70]" />
            <p className="mt-2 text-sm font-medium text-[#c9c1d3]">No verification contacts</p>
            <p className="mt-1 text-xs text-[#81798c]">Import or create supplier contacts before assigning caller PINs.</p>
          </div>
        ) : (
          <div className="grid gap-5 lg:grid-cols-[minmax(0,0.85fr)_minmax(0,1.15fr)]">
            <div>
              <label htmlFor="verification-contact" className="text-xs font-medium text-[#c9c1d3]">Contact</label>
              <select id="verification-contact" value={selectedId} onChange={(event) => onSelect(event.target.value)} className={`${controlClass} mt-1.5`}>
                {contacts.map((contact) => <option key={contact.supplier_id} value={contact.supplier_id}>{contact.name} · {contact.phone_masked}</option>)}
              </select>

              {selectedContact && (
                <div className="mt-3 rounded-xl border border-[#302840]/70 bg-[#10101b]/70 p-4">
                  <div className="flex items-center justify-between gap-3">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-semibold text-white">{selectedContact.name}</p>
                      <p className="mt-0.5 font-mono text-xs text-[#94a3b8]">{selectedContact.phone_masked}</p>
                    </div>
                    <span className={`shrink-0 rounded-full border px-2.5 py-1 text-[9px] font-bold uppercase tracking-wider ${selectedContact.locked ? "border-[#ff2d78]/30 bg-[#ff2d78]/10 text-[#ff9bbd]" : selectedContact.pin_configured ? "border-[#00ffcc]/30 bg-[#00ffcc]/10 text-[#00ffcc]" : "border-[#ffe04a]/30 bg-[#ffe04a]/10 text-[#ffe04a]"}`}>
                      {selectedContact.locked ? "Locked" : selectedContact.requires_rotation ? "Rotation required" : selectedContact.pin_configured ? "Configured" : "Not configured"}
                    </span>
                  </div>
                  <p className="mt-3 border-t border-[#28283c] pt-3 text-[10px] text-[#81798c]">
                    Last PIN update: <span className="text-[#a9a1b4]">{formatTimestamp(selectedContact.pin_updated_at)}</span>
                    {selectedContact.locked && <span className="mt-2 block text-[#ff9bbd]">Locked after repeated failed attempts. Setting a new PIN clears the lockout immediately.</span>}
                    {!selectedContact.locked && selectedContact.requires_rotation && <span className="mt-2 block text-[#ffe04a]">A legacy credential must be replaced by an owner.</span>}
                  </p>
                </div>
              )}
            </div>

            {canManage && selectedContact ? (
              <form onSubmit={submitPin} aria-busy={saving} className="rounded-xl border border-[#302840]/70 bg-[#10101b]/70 p-4">
                <div className="flex items-center gap-2 text-xs font-semibold text-[#e8e0f0]"><Lock size={14} className="text-[#00ffcc]" />{selectedContact.pin_configured ? "Reset PIN" : "Set PIN"}</div>
                <p className="mt-1 text-[10px] leading-4 text-[#81798c]">Use 4–8 digits. The value is sent only when you submit and is immediately cleared from the form.</p>
                <div className="mt-4 grid gap-3 sm:grid-cols-2">
                  <label className="space-y-1.5">
                    <span className="text-xs text-[#c9c1d3]">New PIN</span>
                    <input
                      type="password"
                      inputMode="numeric"
                      autoComplete="new-password"
                      minLength={4}
                      maxLength={8}
                      pattern="[0-9]{4,8}"
                      required
                      value={pin}
                      onChange={(event) => setPin(event.target.value.replace(/\D/g, "").slice(0, 8))}
                      className={controlClass}
                      aria-describedby="pin-rules"
                    />
                  </label>
                  <label className="space-y-1.5">
                    <span className="text-xs text-[#c9c1d3]">Confirm PIN</span>
                    <input
                      type="password"
                      inputMode="numeric"
                      autoComplete="new-password"
                      minLength={4}
                      maxLength={8}
                      pattern="[0-9]{4,8}"
                      required
                      value={confirmPin}
                      onChange={(event) => setConfirmPin(event.target.value.replace(/\D/g, "").slice(0, 8))}
                      className={controlClass}
                    />
                  </label>
                </div>
                <p id="pin-rules" className="mt-2 text-[10px] text-[#756d80]">Digits only · never displayed after submission</p>
                {error && <p role="alert" className="mt-3 text-xs text-[#ff9bbd]">{error}</p>}
                <button type="submit" disabled={saving} className="mt-4 inline-flex items-center gap-2 rounded-xl border border-[#00ffcc]/40 bg-[#00ffcc]/10 px-4 py-2.5 text-xs font-bold text-[#bfffee] transition hover:bg-[#00ffcc]/15 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#00ffcc]/50 disabled:cursor-wait disabled:opacity-50">
                  {saving ? <RefreshCw size={14} className="animate-spin" /> : <ShieldCheck size={14} />}
                  {saving ? "Updating…" : selectedContact.pin_configured ? "Reset PIN" : "Set PIN"}
                </button>
              </form>
            ) : (
              <div className="flex min-h-40 items-center rounded-xl border border-[#302840]/70 bg-[#10101b]/50 p-4">
                <div>
                  <div className="flex items-center gap-2 text-xs font-semibold text-[#c9c1d3]"><Lock size={14} className="text-[#81798c]" />PIN controls are read only</div>
                  <p className="mt-2 text-xs leading-5 text-[#81798c]">Only a non-demo workspace owner can set or reset caller verification PINs. Stored secrets and hashes are never returned to this page.</p>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </section>
  );
}

export default function TelephonySettings() {
  const { activeTenantId, activeTenant, demoMode } = useTenant();
  const [editorMode, setEditorMode] = useState<"create" | "edit" | null>(null);
  const [originalPhone, setOriginalPhone] = useState<string | null>(null);
  const [phoneForm, setPhoneForm] = useState<TelephonyPhoneNumberInput>(EMPTY_PHONE_FORM);
  const [phoneFormError, setPhoneFormError] = useState<string | null>(null);
  const [confirmingDeactivation, setConfirmingDeactivation] = useState<string | null>(null);
  const [selectedContactId, setSelectedContactId] = useState("");
  const [busyAction, setBusyAction] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const { data, error, isLoading, mutate } = useSWR<TelephonySettingsResponse>(
    activeTenantId ? ["telephony-settings", activeTenantId] : null,
    () => api.telephonySettings(activeTenantId),
    { revalidateOnFocus: true },
  );

  const canManage = Boolean(activeTenantId) && !demoMode && activeTenant.role === "owner";
  const routingIsFailClosed = data?.routing_mode === "exact_did";
  const sortedLines = useMemo(
    () => [...(data?.phone_numbers ?? [])].sort((left, right) => Number(right.active) - Number(left.active) || left.label.localeCompare(right.label)),
    [data?.phone_numbers],
  );
  const activeLineCount = data?.phone_numbers.filter((line) => line.active).length ?? 0;
  const protectedLineCount = data?.phone_numbers.filter((line) => line.active && line.verification_mode === "enhanced").length ?? 0;
  const configuredContactCount = data?.verification_contacts.filter((contact) => contact.pin_configured).length ?? 0;

  useEffect(() => {
    setEditorMode(null);
    setOriginalPhone(null);
    setPhoneForm(EMPTY_PHONE_FORM);
    setPhoneFormError(null);
    setConfirmingDeactivation(null);
    setSelectedContactId("");
    setBusyAction(null);
    setSuccess(null);
    setActionError(null);
  }, [activeTenantId]);

  useEffect(() => {
    const contacts = data?.verification_contacts ?? [];
    if (!contacts.length) {
      setSelectedContactId("");
      return;
    }
    if (!contacts.some((contact) => contact.supplier_id === selectedContactId)) {
      setSelectedContactId(contacts[0].supplier_id);
    }
  }, [data?.verification_contacts, selectedContactId]);

  function clearNotices() {
    setSuccess(null);
    setActionError(null);
  }

  function openCreateEditor() {
    clearNotices();
    setPhoneFormError(null);
    setOriginalPhone(null);
    setPhoneForm(EMPTY_PHONE_FORM);
    setEditorMode("create");
  }

  function openEditEditor(line: TelephonyPhoneNumber) {
    if (!canManage) return;
    clearNotices();
    setPhoneFormError(null);
    setOriginalPhone(line.phone_number);
    setPhoneForm({
      phone_number: line.phone_number,
      label: line.label,
      provider: line.provider,
      verification_mode: line.verification_mode,
      route_language: line.route_language,
      active: line.active,
    });
    setEditorMode("edit");
  }

  function closeEditor() {
    setEditorMode(null);
    setOriginalPhone(null);
    setPhoneFormError(null);
  }

  async function savePhoneNumber(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canManage || !editorMode) return;

    const normalizedPhone = phoneForm.phone_number.replace(/[\s()-]/g, "");
    const normalizedLabel = phoneForm.label.trim();
    if (!/^\+[1-9][0-9]{7,14}$/.test(normalizedPhone)) {
      setPhoneFormError("Enter a valid E.164 phone number, such as +442079460123.");
      return;
    }
    if (normalizedLabel.length < 2) {
      setPhoneFormError("Line label must contain at least 2 characters.");
      return;
    }

    const payload: TelephonyPhoneNumberInput = { ...phoneForm, phone_number: normalizedPhone, label: normalizedLabel };
    setPhoneFormError(null);
    clearNotices();
    setBusyAction("save-phone");
    try {
      if (editorMode === "create") {
        await api.createPhoneNumber(activeTenantId, payload);
        setSuccess(`${normalizedPhone} was added to exact DID routing.`);
      } else if (originalPhone) {
        await api.updatePhoneNumber(activeTenantId, originalPhone, payload);
        setSuccess(`${normalizedPhone} was updated.`);
      }
      closeEditor();
      await mutate();
    } catch {
      setPhoneFormError("The mapping could not be saved. Check that the number is unique and try again.");
    } finally {
      setBusyAction(null);
    }
  }

  async function deactivatePhoneNumber(phoneNumber: string) {
    if (!canManage) return;
    clearNotices();
    setBusyAction(`deactivate:${phoneNumber}`);
    try {
      await api.deactivatePhoneNumber(activeTenantId, phoneNumber);
      setConfirmingDeactivation(null);
      setSuccess(`${phoneNumber} was deactivated. Unmatched calls remain fail closed.`);
      await mutate();
    } catch {
      setActionError("The phone number could not be deactivated. Its current routing state has not been changed in this view.");
    } finally {
      setBusyAction(null);
    }
  }

  async function savePin(pin: string, confirmPin: string) {
    if (!canManage || !selectedContactId) throw new Error("PIN update not permitted");
    clearNotices();
    setBusyAction("save-pin");
    try {
      await api.setCallerVerificationPin(activeTenantId, selectedContactId, { pin, confirm_pin: confirmPin });
      setSuccess("Caller verification PIN updated. The secret and its hash are not displayed or retained here.");
      await mutate();
    } catch (pinError) {
      setActionError("The caller verification PIN could not be updated.");
      throw pinError;
    } finally {
      setBusyAction(null);
    }
  }

  if (!activeTenantId) {
    return (
      <section className="rounded-2xl border border-[#ffe04a]/30 bg-[#ffe04a]/10 p-5 text-sm text-[#fef3c7]">
        Select an authorized workspace before loading telephony settings.
      </section>
    );
  }

  return (
    <div className="space-y-6">
      <section className="overflow-hidden rounded-2xl border border-[#28283c] bg-[#141422]">
        <div className="relative p-5 sm:p-6">
          <div className="pointer-events-none absolute -right-16 -top-20 h-52 w-52 rounded-full bg-[#00ffcc]/10 blur-3xl" />
          <div className="relative flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
            <div className="flex items-start gap-3">
              <span className="rounded-xl border border-[#00ffcc]/25 bg-[#00ffcc]/10 p-2.5 text-[#00ffcc] shadow-[0_0_18px_rgba(0,255,204,0.08)]"><PhoneCall size={21} /></span>
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <p className="text-[10px] font-mono uppercase tracking-[0.18em] text-[#94a3b8]">Telephony control plane</p>
                  <span className={`rounded-full border px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider ${canManage ? "border-[#00ffcc]/30 bg-[#00ffcc]/10 text-[#00ffcc]" : "border-[#ffe04a]/30 bg-[#ffe04a]/10 text-[#ffe04a]"}`}>{roleLabel(activeTenant.role, demoMode)}</span>
                </div>
                <h2 className="mt-1 text-xl font-bold text-white sm:text-2xl">Inbound lines & caller verification</h2>
                <p className="mt-2 max-w-3xl text-sm leading-6 text-[#94a3b8]">Manage destination-number routing and per-contact PIN posture for {activeTenant.name}. No provider credentials or stored secrets are exposed in the browser.</p>
              </div>
            </div>
            <button type="button" onClick={() => void mutate()} disabled={isLoading} className={secondaryButtonClass}>
              <RefreshCw size={14} className={isLoading ? "animate-spin" : ""} /> Refresh
            </button>
          </div>
        </div>

        <div className={`border-t px-5 py-4 sm:px-6 ${routingIsFailClosed ? "border-[#00ffcc]/20 bg-[#00ffcc]/5" : "border-[#ff2d78]/30 bg-[#ff2d78]/10"}`}>
          <div className="flex items-start gap-3">
            {routingIsFailClosed ? <ShieldCheck size={18} className="mt-0.5 shrink-0 text-[#00ffcc]" /> : <AlertTriangle size={18} className="mt-0.5 shrink-0 text-[#ff2d78]" />}
            <div>
              <p className={`text-xs font-bold ${routingIsFailClosed ? "text-[#bfffee]" : "text-[#fecdd3]"}`}>{routingIsFailClosed ? "Fail-closed exact DID routing" : isLoading ? "Verifying routing posture…" : "Routing posture requires attention"}</p>
              <p className="mt-1 text-xs leading-5 text-[#94a3b8]">
                {routingIsFailClosed
                  ? "Only an active, exact destination-number match creates tenant context. Missing, unknown, and inactive DIDs are rejected—never routed to a default workspace."
                  : isLoading
                    ? "Loading the server-authoritative routing mode."
                    : "The server did not report exact_did mode. Treat unmatched inbound routing as unavailable until an owner or operator confirms the backend posture."}
              </p>
            </div>
          </div>
        </div>
      </section>

      {!canManage && (
        <div className="flex items-start gap-3 rounded-2xl border border-[#ffe04a]/25 bg-[#ffe04a]/10 p-4 text-sm text-[#fef3c7]">
          <Lock size={17} className="mt-0.5 shrink-0" />
          <p><strong>Read-only settings.</strong> {demoMode ? "Demo mode cannot change live routing or caller secrets." : `${activeTenant.role === "operator" ? "Operators" : "Viewers"} can inspect telephony posture, but only a workspace owner can add, edit, deactivate, or update PINs.`}</p>
        </div>
      )}

      {error && (
        <div role="alert" className="flex flex-col gap-3 rounded-2xl border border-[#ff2d78]/35 bg-[#ff2d78]/10 p-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-start gap-3"><AlertTriangle size={17} className="mt-0.5 shrink-0 text-[#ff9bbd]" /><div><p className="text-sm font-semibold text-[#fecdd3]">Telephony settings could not be loaded.</p><p className="mt-1 text-xs text-[#d9a5b7]">No routing or caller-verification change is available while server state is unknown.</p></div></div>
          <button type="button" onClick={() => void mutate()} className={secondaryButtonClass}><RefreshCw size={14} /> Retry</button>
        </div>
      )}

      {(success || actionError) && (
        <div aria-live="polite" role={actionError ? "alert" : "status"} className={`flex items-start gap-3 rounded-xl border px-4 py-3 text-sm ${actionError ? "border-[#ff2d78]/35 bg-[#ff2d78]/10 text-[#fecdd3]" : "border-[#00ffcc]/30 bg-[#00ffcc]/10 text-[#bfffee]"}`}>
          {actionError ? <AlertTriangle size={17} className="mt-0.5 shrink-0" /> : <CheckCircle2 size={17} className="mt-0.5 shrink-0" />}
          <p>{actionError || success}</p>
        </div>
      )}

      {isLoading && !data ? (
        <div aria-label="Loading telephony settings" className="grid animate-pulse gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {[0, 1, 2, 3].map((item) => <div key={item} className="h-24 rounded-2xl border border-[#28283c] bg-[#141422]/60" />)}
        </div>
      ) : data ? (
        <>
          <section aria-label="Telephony posture summary" className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <div className="rounded-2xl border border-[#302840]/70 bg-[#141422]/55 p-4"><div className="flex items-center justify-between"><p className="text-[9px] font-mono uppercase tracking-wider text-[#81798c]">Routing mode</p><Radio size={15} className={routingIsFailClosed ? "text-[#00ffcc]" : "text-[#ff2d78]"} /></div><p className="mt-2 text-lg font-bold text-white">{routingIsFailClosed ? "Exact DID" : "Unverified"}</p><p className="mt-1 text-[10px] text-[#81798c]">{routingIsFailClosed ? "Fail closed on no match" : "Treat routing as unavailable"}</p></div>
            <div className="rounded-2xl border border-[#302840]/70 bg-[#141422]/55 p-4"><div className="flex items-center justify-between"><p className="text-[9px] font-mono uppercase tracking-wider text-[#81798c]">Active lines</p><PhoneCall size={15} className="text-[#ff2d78]" /></div><p className="mt-2 text-lg font-bold text-white">{activeLineCount}</p><p className="mt-1 text-[10px] text-[#81798c]">{data.phone_numbers.length} total mappings</p></div>
            <div className="rounded-2xl border border-[#302840]/70 bg-[#141422]/55 p-4"><div className="flex items-center justify-between"><p className="text-[9px] font-mono uppercase tracking-wider text-[#81798c]">PIN-protected lines</p><ShieldCheck size={15} className="text-[#ffe04a]" /></div><p className="mt-2 text-lg font-bold text-white">{protectedLineCount}</p><p className="mt-1 text-[10px] text-[#81798c]">Active lines requiring PIN</p></div>
            <div className="rounded-2xl border border-[#302840]/70 bg-[#141422]/55 p-4"><div className="flex items-center justify-between"><p className="text-[9px] font-mono uppercase tracking-wider text-[#81798c]">Configured contacts</p><KeyRound size={15} className="text-[#00ffcc]" /></div><p className="mt-2 text-lg font-bold text-white">{configuredContactCount}</p><p className="mt-1 text-[10px] text-[#81798c]">of {data.verification_contacts.length} contacts</p></div>
          </section>

          <section className="rounded-2xl border border-[#302840]/70 bg-[#141422]/55 overflow-hidden">
            <div className="flex flex-col gap-3 border-b border-[#302840]/50 bg-[#0f0f1a]/70 px-5 py-4 sm:flex-row sm:items-center sm:justify-between sm:px-6">
              <div className="flex items-center gap-3"><span className="rounded-xl border border-[#ff2d78]/25 bg-[#ff2d78]/10 p-2 text-[#ff2d78]"><Radio size={18} /></span><div><h2 className="text-base font-bold text-white">Inbound phone lines</h2><p className="mt-0.5 text-xs text-[#94a3b8]">Destination numbers mapped to this workspace</p></div></div>
              <button type="button" onClick={openCreateEditor} disabled={!canManage || Boolean(editorMode)} aria-expanded={editorMode === "create"} aria-controls="phone-number-editor" className="inline-flex items-center justify-center gap-2 rounded-xl bg-[#ff2d78] px-4 py-2.5 text-xs font-bold text-white transition hover:shadow-[0_0_18px_rgba(255,45,120,0.24)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#ff2d78]/60 disabled:cursor-not-allowed disabled:opacity-40" title={canManage ? "Add an inbound line" : "Only a workspace owner can add lines"}><Plus size={14} /> Add line</button>
            </div>

            <div className="space-y-4 p-4 sm:p-6">
              {editorMode && (
                <PhoneNumberEditor mode={editorMode} value={phoneForm} saving={busyAction === "save-phone"} error={phoneFormError} onChange={setPhoneForm} onCancel={closeEditor} onSubmit={savePhoneNumber} />
              )}

              {sortedLines.length === 0 ? (
                <div className="rounded-2xl border border-dashed border-[#302840] bg-[#10101b]/50 px-4 py-10 text-center"><Globe2 size={25} className="mx-auto text-[#655d70]" /><p className="mt-3 text-sm font-semibold text-[#c9c1d3]">No destination numbers configured</p><p className="mx-auto mt-1 max-w-md text-xs leading-5 text-[#81798c]">Inbound calls remain fail closed until an owner adds an active exact DID mapping.</p></div>
              ) : (
                <div className="space-y-3">
                  {sortedLines.map((line) => (
                    <PhoneLineCard
                      key={line.phone_number}
                      line={line}
                      canManage={canManage}
                      confirming={confirmingDeactivation === line.phone_number}
                      busy={busyAction === `deactivate:${line.phone_number}`}
                      onEdit={() => openEditEditor(line)}
                      onRequestDeactivate={() => { clearNotices(); setConfirmingDeactivation(line.phone_number); }}
                      onCancelDeactivate={() => setConfirmingDeactivation(null)}
                      onConfirmDeactivate={() => void deactivatePhoneNumber(line.phone_number)}
                    />
                  ))}
                </div>
              )}
            </div>
          </section>

          <VerificationPanel
            contacts={data.verification_contacts}
            selectedId={selectedContactId}
            canManage={canManage}
            saving={busyAction === "save-pin"}
            onSelect={setSelectedContactId}
            onSaved={savePin}
          />
        </>
      ) : null}
    </div>
  );
}
