"""Regression tests for the caller-identification chain.

All three bugs here were live simultaneously and produced a green self-test.

`lookup_supplier` stripped non-digits from the phone argument and matched with
`LIKE '%<digits>%'`. When the model passed the literal string "caller's phone
number" — which it did, because nothing in its context carried the real one —
that reduced to `LIKE '%'`, matching every supplier in the tenant. `.first()`
returned an arbitrary company, the agent greeted the caller by that company's
name, and `session.supplier_id` was set to it.

That last part is what made it serious rather than merely embarrassing:
`session.supplier_id` is the record `verify_caller` checks against. And
`lookup_supplier` returned `city`, `gstin` and `contact_person` in its result —
the three values `verify_caller` accepts as its second factor. The model was
handed the answers to its own security question and could pass them straight
back, verifying a stranger against a record they had proved nothing about.
"""

from __future__ import annotations

import pytest

from voxflow_api.agent.tools import lookup_supplier, verify_caller
from voxflow_api.db import Supplier, session_scope
from voxflow_api.voice.pipeline import CallSession


@pytest.fixture
def two_contacts():
    """Two suppliers in one tenant, so a wildcard match is detectable."""
    from voxflow_api.db import Tenant

    with session_scope() as db:
        if not db.get(Tenant, "t-ident"):
            db.add(Tenant(id="t-ident", name="Identification Test Co"))
    with session_scope() as db:
        db.query(Supplier).filter(Supplier.tenant_id == "t-ident").delete()
        db.add(Supplier(id="s-first", tenant_id="t-ident", name="Aardvark Traders",
                        phone="+919000000001", city="Pune", state="MH",
                        pincode="411001", contact_person="Asha Rao",
                        gstin="27AAAAA0000A1Z5"))
        db.add(Supplier(id="s-second", tenant_id="t-ident", name="Zebra Wholesale",
                        phone="+919000000002", city="Indore", state="MP",
                        pincode="452001", contact_person="Zoya Khan",
                        gstin="23ZZZZZ9999Z9Z9"))
    yield
    with session_scope() as db:
        db.query(Supplier).filter(Supplier.tenant_id == "t-ident").delete()


def _session() -> CallSession:
    return CallSession(call_id="t-ident-call", tenant_id="t-ident")


# ── the wildcard ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "junk",
    [
        "caller's phone number",   # what the model actually passed
        "unknown", "", "  ", "the number from metadata", "N/A", "+", "1234",
    ],
)
async def test_junk_phone_never_matches_anyone(two_contacts, junk: str) -> None:
    s = _session()
    r = await lookup_supplier(s, phone=junk)
    assert r["found"] is False, (
        f"phone={junk!r} identified {r.get('name')!r} — a caller would be greeted "
        "as a company they have nothing to do with"
    )
    assert s.supplier_id is None, "supplier_id was set from a non-match"
    assert s.identified_by_phone is False


@pytest.mark.asyncio
async def test_real_phone_still_matches(two_contacts) -> None:
    s = _session()
    r = await lookup_supplier(s, phone="+919000000002")
    assert r["found"] is True
    assert r["name"] == "Zebra Wholesale"
    assert r["matched_by"] == "phone"
    assert s.identified_by_phone is True


@pytest.mark.asyncio
async def test_falls_back_to_the_number_from_call_metadata(two_contacts) -> None:
    """The model should not need to pass it at all."""
    s = _session()
    s.caller_phone = "+919000000001"
    r = await lookup_supplier(s)
    assert r["found"] is True and r["name"] == "Aardvark Traders"
    assert s.identified_by_phone is True


@pytest.mark.asyncio
async def test_name_match_is_not_phone_identification(two_contacts) -> None:
    """The caller supplied the name, so it cannot be a factor."""
    s = _session()
    r = await lookup_supplier(s, name="Zebra")
    assert r["found"] is True
    assert r["matched_by"] == "name"
    assert s.identified_by_phone is False


# ── the leaked second factors ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_unverified_result_withholds_every_second_factor(two_contacts) -> None:
    s = _session()
    r = await lookup_supplier(s, phone="+919000000001")
    for secret in ("city", "gstin", "contact_person", "state", "phone"):
        assert secret not in r, (
            f"{secret!r} is disclosed before verification. verify_caller accepts "
            f"city, gstin and contact_person as its second factor, so returning "
            f"them lets the model pass back what it just read."
        )


@pytest.mark.asyncio
async def test_verified_result_may_include_details(two_contacts) -> None:
    s = _session()
    s.verified = True
    r = await lookup_supplier(s, phone="+919000000001")
    assert r["city"] == "Pune" and r["gstin"] == "27AAAAA0000A1Z5"


@pytest.mark.asyncio
async def test_wrong_caller_cannot_verify_against_an_arbitrary_record(two_contacts) -> None:
    """The end-to-end consequence of the two bugs together."""
    s = _session()
    await lookup_supplier(s, phone="caller's phone number")
    r = await verify_caller(s, company="Aardvark Traders", city_or_gstin="Pune")
    assert r["verified"] is False
    assert r["reason"] == "caller_not_identified"
    assert s.verified is False


@pytest.mark.asyncio
async def test_genuine_caller_still_verifies(two_contacts) -> None:
    """The fixes must not break the happy path."""
    s = _session()
    s.caller_phone = "+919000000001"
    await lookup_supplier(s)
    r = await verify_caller(s, company="Aardvark Traders", city_or_gstin="Pune")
    assert r["verified"] is True
    assert s.verified is True


# ── the missing context ────────────────────────────────────────────────────

def test_call_context_gives_the_model_the_real_number() -> None:
    from voxflow_api.agent.runner import AgentRunner

    s = _session()
    s.caller_phone = "+919000000001"
    ctx = AgentRunner._call_context(s)
    assert "+919000000001" in ctx
    assert "NO" in ctx  # unverified state stated explicitly


def test_call_context_is_honest_when_the_number_is_absent() -> None:
    from voxflow_api.agent.runner import AgentRunner

    ctx = AgentRunner._call_context(_session())
    assert "withheld" in ctx
    assert "do not invent" in ctx


def test_call_context_is_actually_sent_to_the_model() -> None:
    """Building the string is useless if it never reaches the history."""
    from voxflow_api.agent.runner import AgentRunner

    s = _session()
    s.caller_phone = "+919000000001"
    history = AgentRunner()._history(s)
    assert any("+919000000001" in (t.content or "") for t in history), (
        "the caller's number is not in the messages sent to the LLM"
    )


@pytest.mark.asyncio
async def test_cache_does_not_leak_a_verified_record_to_an_unverified_call(two_contacts) -> None:
    """The TTL cache is shared across calls within a tenant.

    Verified results are complete; unverified results are redacted. A cache key
    that ignores verification state hands one caller's full record — gstin
    included — to the next unverified caller who happens to dial about the same
    contact.
    """
    verified = _session()
    verified.verified = True
    full = await lookup_supplier(verified, phone="+919000000001")
    assert "gstin" in full  # cached in its complete form

    stranger = _session()  # same tenant, same number, NOT verified
    redacted = await lookup_supplier(stranger, phone="+919000000001")
    for secret in ("gstin", "city", "contact_person"):
        assert secret not in redacted, (
            f"{secret!r} leaked out of the cache to an unverified call"
        )
