"""The checked-in DDL must match the ORM models.

If someone adds a column to db.py and forgets to regenerate
migrations/000_base_schema.sql, a fresh deployment silently gets a database
the code cannot query. That is a production failure discovered during a phone
call. This test turns it into a red CI run.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from voxflow_api.gen_schema import TABLES, table_ddl

SQL = Path(__file__).resolve().parents[3] / "migrations" / "000_base_schema.sql"


@pytest.fixture(scope="module")
def sql_text() -> str:
    if not SQL.exists():  # pragma: no cover
        pytest.skip(f"{SQL} not present")
    return SQL.read_text()


def _columns(ddl: str, table: str) -> set[str]:
    """Column names declared in `table`'s CREATE TABLE block."""
    m = re.search(
        rf"CREATE TABLE IF NOT EXISTS {table} \((.*?)\n\);", ddl, re.S,
    )
    assert m, f"no CREATE TABLE block for {table}"
    cols = set()
    for line in m.group(1).splitlines():
        line = line.strip().rstrip(",")
        if not line or line.startswith(("PRIMARY KEY", "FOREIGN KEY", "UNIQUE", "CONSTRAINT", "CHECK")):
            continue
        cols.add(line.split()[0])
    return cols


def test_every_model_table_is_in_the_file(sql_text: str) -> None:
    for t in TABLES:
        assert f"CREATE TABLE IF NOT EXISTS {t} (" in sql_text, f"{t} missing from 000_base_schema.sql"


def test_columns_match_the_models(sql_text: str) -> None:
    """The exact check that catches "added a column, forgot the migration"."""
    generated = table_ddl()
    for t in TABLES:
        want = _columns(generated, t)
        got = _columns(sql_text, t)
        assert want == got, (
            f"{t}: 000_base_schema.sql is out of sync with db.py.\n"
            f"  missing from SQL: {sorted(want - got)}\n"
            f"  stale in SQL:     {sorted(got - want)}\n"
            f"  Regenerate: python -m voxflow_api.gen_schema"
        )


def test_selftest_expected_tables_all_covered(sql_text: str) -> None:
    """selftest fails the deployment if any of these is absent."""
    from voxflow_api.selftest import _EXPECTED_TABLES, _MIGRATION_COLUMNS

    for t in _EXPECTED_TABLES:
        assert f"CREATE TABLE IF NOT EXISTS {t} (" in sql_text
    for table, cols in _MIGRATION_COLUMNS.items():
        present = _columns(sql_text, table)
        assert set(cols) <= present, f"{table} missing {sorted(set(cols) - present)}"


def test_rls_enabled_on_every_table(sql_text: str) -> None:
    """The project ref is public; without RLS the anon key reads everything."""
    for t in TABLES:
        assert f"ALTER TABLE {t} ENABLE ROW LEVEL SECURITY;" in sql_text, f"RLS not enabled on {t}"


def test_file_is_idempotent(sql_text: str) -> None:
    """It will be pasted into the SQL editor more than once. It must survive that."""
    creates = re.findall(r"CREATE TABLE(?! IF NOT EXISTS)", sql_text)
    assert not creates, "found a CREATE TABLE without IF NOT EXISTS"
    for stmt in re.findall(r"CREATE POLICY (\w+) ON (\w+)", sql_text):
        assert f"DROP POLICY IF EXISTS {stmt[0]} ON {stmt[1]};" in sql_text, (
            f"CREATE POLICY {stmt[0]} ON {stmt[1]} has no preceding DROP POLICY IF EXISTS"
        )
