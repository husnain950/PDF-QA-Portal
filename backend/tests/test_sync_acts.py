import json
from pathlib import Path

import aiosqlite
import pytest

from backend.routes.documents import list_documents
from backend.sync_acts import discover_pairs, run_sync
from backend.tests.conftest import sample_document, write_pair


def test_pair_discovery_rejects_ambiguous_and_symbolic_sources(tmp_path):
    ambiguous = tmp_path / "Ambiguous"
    ambiguous.mkdir()
    (ambiguous / "one.pdf").write_bytes(b"%PDF")
    (ambiguous / "two.pdf").write_bytes(b"%PDF")
    (ambiguous / "one.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="expected one PDF and one JSON"):
        discover_pairs(tmp_path)

    for child in ambiguous.iterdir():
        child.unlink()
    ambiguous.rmdir()
    outside = tmp_path.parent / f"{tmp_path.name}-outside"
    outside.mkdir()
    (tmp_path / "Linked Act").symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match="symbolic-link directories"):
        discover_pairs(tmp_path)


@pytest.mark.asyncio
async def test_sync_is_idempotent_and_keeps_fts_and_api_consistent(
    runtime_sandbox,
):
    source = runtime_sandbox["root"] / "export"
    write_pair(source)

    first = await run_sync(source)
    second = await run_sync(source)

    assert first["added"] == 1
    assert first["failed"] == 0
    assert second["skipped"] == 1
    assert second["added"] == second["updated"] == second["failed"] == 0

    async with aiosqlite.connect(runtime_sandbox["db_path"]) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA foreign_keys = ON")
        documents = await list_documents(db)
        assert len(documents) == 1
        assert documents[0].source_type == "acts_corpus"
        assert documents[0].source_key == "Test Act"
        async with db.execute("SELECT COUNT(*) FROM sections") as cursor:
            section_count = (await cursor.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM sections_fts") as cursor:
            fts_count = (await cursor.fetchone())[0]
        async with db.execute("PRAGMA foreign_key_check") as cursor:
            foreign_key_errors = await cursor.fetchall()

    assert section_count == fts_count == 2
    assert foreign_key_errors == []
    assert len(list(Path(runtime_sandbox["upload_dir"]).iterdir())) == 2


@pytest.mark.asyncio
async def test_changed_annotated_source_rolls_back_document_and_files(
    runtime_sandbox,
):
    source = runtime_sandbox["root"] / "export"
    pair_directory = write_pair(source)
    first = await run_sync(source)
    assert first["added"] == 1

    async with aiosqlite.connect(runtime_sandbox["db_path"]) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT d.id AS document_id, d.source_hash, s.id AS section_id
            FROM documents d JOIN sections s ON s.document_id = d.id
            ORDER BY s.sort_order LIMIT 1
            """
        ) as cursor:
            before = dict(await cursor.fetchone())
        await db.execute(
            """
            INSERT INTO annotations (
                id, section_id, highlighted_text, start_offset, end_offset,
                severity, created_at, status
            ) VALUES ('annotation-1', ?, 'First', 0, 5, 'error', 'now', 'open')
            """,
            (before["section_id"],),
        )
        await db.commit()

    payload = json.loads(sample_document())
    payload["chapters"][0]["sections"][0]["plain_text"] = "Changed first section"
    (pair_directory / "act.json").write_text(
        json.dumps(payload),
        encoding="utf-8",
    )
    result = await run_sync(source)
    assert result["failed"] == 1

    async with aiosqlite.connect(runtime_sandbox["db_path"]) as db:
        async with db.execute(
            "SELECT source_hash FROM documents WHERE id = ?",
            (before["document_id"],),
        ) as cursor:
            after_hash = (await cursor.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM annotations") as cursor:
            annotation_count = (await cursor.fetchone())[0]
    assert after_hash == before["source_hash"]
    assert annotation_count == 1
    assert len(list(Path(runtime_sandbox["upload_dir"]).iterdir())) == 2
