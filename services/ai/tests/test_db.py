"""Test veritabanının eklentilerini ve testlerin birbirinden yalıtılmasını test eder."""

import psycopg
import pytest
from psycopg.rows import TupleRow


@pytest.mark.asyncio
async def test_extensions_are_installed(db: psycopg.AsyncConnection[TupleRow]) -> None:
    """Migration'ların açtığı vector ve pg_textsearch eklentileri yüklüdür."""
    cursor = await db.execute("SELECT extname FROM pg_extension")
    extensions = {row[0] for row in await cursor.fetchall()}

    assert {"vector", "pg_textsearch"} <= extensions


@pytest.mark.asyncio
async def test_changes_are_invisible_to_other_connections(
    db: psycopg.AsyncConnection[TupleRow], database_url: str
) -> None:
    """Testin geri alınacak değişikliğini başka bir bağlantı göremez."""
    await db.execute("CREATE TABLE isolation_probe (id integer)")

    async with await psycopg.AsyncConnection.connect(database_url) as other:
        cursor = await other.execute("SELECT to_regclass('isolation_probe')")
        row = await cursor.fetchone()

    assert row == (None,)
