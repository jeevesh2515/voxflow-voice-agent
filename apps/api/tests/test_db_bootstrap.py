"""Regression coverage for free-tier-safe database startup behavior."""

from __future__ import annotations

import pytest

from voxflow_api import db


@pytest.mark.parametrize(
    ("mode", "dialect", "expected"),
    [
        ("auto", "sqlite", True),
        ("auto", "postgresql", False),
        ("always", "sqlite", True),
        ("always", "postgresql", True),
        ("skip", "sqlite", False),
        ("skip", "postgresql", False),
    ],
)
def test_schema_bootstrap_mode_is_explicit_and_dialect_safe(
    mode: str, dialect: str, expected: bool
) -> None:
    assert db.should_bootstrap_schema(mode=mode, dialect_name=dialect) is expected


def test_schema_bootstrap_mode_rejects_unknown_values() -> None:
    with pytest.raises(ValueError, match="unsupported database bootstrap mode"):
        db.should_bootstrap_schema(mode="unsafe", dialect_name="postgresql")


class _Inspector:
    def __init__(self, tables: set[str]) -> None:
        self._tables = tables

    def get_table_names(self) -> list[str]:
        return sorted(self._tables)


def test_schema_verification_accepts_all_mapped_tables(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(db, "inspect", lambda _engine: _Inspector(set(db.Base.metadata.tables)))
    db.verify_schema_tables()


def test_schema_verification_fails_closed_when_migration_tables_are_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(db, "inspect", lambda _engine: _Inspector(set()))

    with pytest.raises(RuntimeError, match="apply the reviewed migrations"):
        db.verify_schema_tables()
