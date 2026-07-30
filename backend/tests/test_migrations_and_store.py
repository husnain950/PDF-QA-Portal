import sqlite3
import uuid

import aiosqlite
import pytest

import backend.database as database
from backend.services.document_store import ReviewConflict, apply_parsed_document
from backend.services.json_parser import parse_json_document
from backend.tests.conftest import sample_document


@pytest.mark.asyncio
async def test_migration_adds_source_columns_and_unique_indexes(monkeypatch, tmp_path):
    db_path = tmp_path / "legacy.db"
    connection = sqlite3.connect(db_path)
    connection.executescript(
        """
        CREATE TABLE documents (
            id TEXT PRIMARY KEY, name TEXT NOT NULL, pdf_filename TEXT NOT NULL,
            json_filename TEXT NOT NULL, total_sections INTEGER NOT NULL,
            total_pages INTEGER NOT NULL, uploaded_at TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending'
        );
        CREATE TABLE sections (
            id TEXT PRIMARY KEY, document_id TEXT NOT NULL,
            chapter_code TEXT, chapter_heading TEXT, part_code TEXT,
            part_heading TEXT, division_code TEXT, division_heading TEXT,
            section_code TEXT NOT NULL, section_heading TEXT NOT NULL,
            start_page INTEGER, end_page INTEGER, html_content TEXT,
            plain_text TEXT, sort_order INTEGER NOT NULL,
            review_status TEXT NOT NULL DEFAULT 'pending'
        );
        """
    )
    connection.commit()
    connection.close()

    monkeypatch.setattr(database, "DB_DIR", str(tmp_path))
    monkeypatch.setattr(database, "DB_PATH", str(db_path))
    await database.init_db()

    connection = sqlite3.connect(db_path)
    document_columns = {
        row[1] for row in connection.execute("PRAGMA table_info(documents)")
    }
    section_columns = {
        row[1] for row in connection.execute("PRAGMA table_info(sections)")
    }
    indexes = {
        row[1] for row in connection.execute("PRAGMA index_list(sections)")
    }
    connection.close()

    assert {"source_type", "source_key", "source_hash"} <= document_columns
    assert "source_key" in section_columns
    assert "idx_sections_source" in indexes


@pytest.mark.asyncio
async def test_store_preserves_state_and_rejects_annotated_content_changes(
    runtime_sandbox,
):
    document_id = "store-document"
    sections, footnotes = parse_json_document(
        sample_document(),
        document_id=document_id,
    )
    async with aiosqlite.connect(runtime_sandbox["db_path"]) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA foreign_keys = ON")
        await db.execute(
            """
            INSERT INTO documents (
                id, name, pdf_filename, json_filename, total_sections,
                total_pages, uploaded_at, status, source_type
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                document_id,
                "Store Act",
                "act.pdf",
                "act.json",
                2,
                3,
                "2026-07-29T00:00:00Z",
                "pending",
                "upload",
            ),
        )
        await apply_parsed_document(db, document_id, sections, footnotes)
        first_id = sections[0]["id"]
        second_id = sections[1]["id"]
        await db.execute(
            "UPDATE sections SET review_status = 'approved' WHERE id IN (?, ?)",
            (first_id, second_id),
        )
        await db.execute(
            """
            INSERT INTO annotations (
                id, section_id, highlighted_text, start_offset, end_offset,
                issue_description, severity, created_at, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                first_id,
                "First",
                0,
                5,
                "Check extraction",
                "error",
                "2026-07-29T00:00:00Z",
                "open",
            ),
        )
        await db.commit()

        identical_stats = await apply_parsed_document(
            db,
            document_id,
            sections,
            footnotes,
        )
        assert identical_stats["approved"] == 2

        changed_sections, changed_footnotes = parse_json_document(
            sample_document(second_text="Corrected second section"),
            document_id=document_id,
        )
        changed_sections[0]["plain_text"] = "Changed annotated content"
        with pytest.raises(ReviewConflict, match="changed with 1 annotation"):
            await apply_parsed_document(
                db,
                document_id,
                changed_sections,
                changed_footnotes,
            )
        await db.rollback()

        changed_sections[0] = sections[0]
        stats = await apply_parsed_document(
            db,
            document_id,
            changed_sections,
            changed_footnotes,
        )
        await db.commit()
        assert stats["approved"] == 1
        assert stats["pending"] == 1
        async with db.execute(
            "SELECT review_status FROM sections WHERE id = ?",
            (second_id,),
        ) as cursor:
            assert (await cursor.fetchone())[0] == "pending"


@pytest.mark.asyncio
async def test_store_rejects_removing_reviewed_evidence(runtime_sandbox):
    document_id = "remove-document"
    sections, footnotes = parse_json_document(
        sample_document(),
        document_id=document_id,
    )
    async with aiosqlite.connect(runtime_sandbox["db_path"]) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA foreign_keys = ON")
        await db.execute(
            """
            INSERT INTO documents (
                id, name, pdf_filename, json_filename, total_sections,
                total_pages, uploaded_at, status, source_type
            ) VALUES (?, 'Act', 'a.pdf', 'a.json', 2, 3, 'now', 'pending', 'upload')
            """,
            (document_id,),
        )
        await apply_parsed_document(db, document_id, sections, footnotes)
        await db.execute(
            "UPDATE sections SET review_status = 'approved' WHERE id = ?",
            (sections[1]["id"],),
        )
        await db.commit()

        with pytest.raises(ReviewConflict, match="was removed with QA state"):
            await apply_parsed_document(
                db,
                document_id,
                sections[:1],
                footnotes,
            )
        await db.rollback()


@pytest.mark.asyncio
async def test_store_rejects_reviewed_footnote_removed_with_pending_section(
    runtime_sandbox,
):
    document_id = "footnote-remove-document"
    sections, footnotes = parse_json_document(
        sample_document(),
        document_id=document_id,
    )
    async with aiosqlite.connect(runtime_sandbox["db_path"]) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA foreign_keys = ON")
        await db.execute(
            """
            INSERT INTO documents (
                id, name, pdf_filename, json_filename, total_sections,
                total_pages, uploaded_at, status, source_type
            ) VALUES (?, 'Act', 'a.pdf', 'a.json', 2, 3, 'now', 'pending', 'upload')
            """,
            (document_id,),
        )
        await apply_parsed_document(db, document_id, sections, footnotes)
        await db.execute(
            "UPDATE footnotes SET review_status = 'approved' WHERE id = ?",
            (footnotes[0]["id"],),
        )
        await db.commit()

        with pytest.raises(ReviewConflict, match="footnote 1 was removed"):
            await apply_parsed_document(
                db,
                document_id,
                sections[1:],
                [],
            )
        await db.rollback()
