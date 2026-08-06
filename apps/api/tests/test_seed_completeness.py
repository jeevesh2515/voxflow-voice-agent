"""A plain `python -m voxflow_api.seed` must produce a demoable database.

The history block (orders, shipments, calls) used to be gated behind `--reset`.
So the documented command produced tenants, products, suppliers and stock but
zero orders — and orders are the only thing the customer-support flow reads.
You would see "seed.done", ring in to ask whether your PO had been signed, and
the agent would correctly tell you no such order exists. Nothing would look
broken anywhere.
"""

from __future__ import annotations

import subprocess
import sys
import textwrap


def test_seed_without_reset_creates_orders(tmp_path) -> None:
    """The exact command in SETUP.md, against an empty database."""
    db = tmp_path / "seed_check.db"
    script = textwrap.dedent(
        """
        from voxflow_api.db import Order, Supplier, Tenant, session_scope
        from voxflow_api.seed import seed

        seed()                      # no --reset, as documented

        with session_scope() as s:
            print("tenants", s.query(Tenant).count())
            print("contacts", s.query(Supplier).count())
            print("orders", s.query(Order).count())
        """
    )
    r = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True, text=True, timeout=180,
        env={"PATH": "/usr/bin:/bin", "DATABASE_URL": f"sqlite:///{db}",
             "PYTHONPATH": str(__import__("pathlib").Path(__file__).resolve().parents[1])},
    )
    assert r.returncode == 0, r.stderr[-2000:]
    counts = dict(
        (ln.split()[0], int(ln.split()[1]))
        for ln in r.stdout.splitlines() if ln.split() and ln.split()[0] in {"tenants", "contacts", "orders"}
    )
    assert counts["tenants"] > 0
    assert counts["contacts"] > 0
    assert counts["orders"] > 0, (
        "plain `seed` produced no orders — the customer-support flow has nothing to read"
    )


def test_seed_is_idempotent(tmp_path) -> None:
    """It will be run twice. The second run must not duplicate or crash."""
    db = tmp_path / "twice.db"
    script = textwrap.dedent(
        """
        from voxflow_api.db import Order, session_scope
        from voxflow_api.seed import seed
        seed(); seed()
        with session_scope() as s:
            print("orders", s.query(Order).count())
        """
    )
    r = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True, text=True, timeout=240,
        env={"PATH": "/usr/bin:/bin", "DATABASE_URL": f"sqlite:///{db}",
             "PYTHONPATH": str(__import__("pathlib").Path(__file__).resolve().parents[1])},
    )
    assert r.returncode == 0, r.stderr[-2000:]
    n = int([ln for ln in r.stdout.splitlines() if ln.startswith("orders")][0].split()[1])
    assert n == 4, f"expected the 4 demo orders exactly once, got {n}"


def test_prompt_forbids_tool_free_answers() -> None:
    """The agent answered a direct order question with a bare greeting."""
    from voxflow_api.agent.prompts import SYSTEM_PROMPT

    assert "Tools are not optional" in SYSTEM_PROMPT
    assert "greeting on its own is never a complete turn" in SYSTEM_PROMPT.lower() or \
           "A greeting on its own is never a complete turn" in SYSTEM_PROMPT
