import io

import aiosqlite
import pytest
from fastapi import HTTPException, UploadFile

from backend.models import FootnoteStatusUpdate
from backend.routes.documents import replace_json
from backend.routes.footnotes import update_footnote_status
from backend.sync_acts import run_sync
from backend.tests.conftest import sample_document, write_pair


@pytest.mark.asyncio
async def test_footnote_revert_restores_document_pending_status(runtime_sandbox):
    source = runtime_sandbox["root"] / "export"
    write_pair(source)
    await run_sync(source)

    async with aiosqlite.connect(runtime_sandbox["db_path"]) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT f.id AS footnote_id, d.id AS document_id
            FROM footnotes f
            JOIN sections s ON s.id = f.section_id
            JOIN documents d ON d.id = s.document_id
            LIMIT 1
            """
        ) as cursor:
            row = await cursor.fetchone()

        await update_footnote_status(
            row["footnote_id"],
            FootnoteStatusUpdate(review_status="approved"),
            db,
        )
        async with db.execute(
            "SELECT status FROM documents WHERE id = ?",
            (row["document_id"],),
        ) as cursor:
            assert (await cursor.fetchone())["status"] == "in_progress"

        await update_footnote_status(
            row["footnote_id"],
            FootnoteStatusUpdate(review_status="pending"),
            db,
        )
        async with db.execute(
            "SELECT status FROM documents WHERE id = ?",
            (row["document_id"],),
        ) as cursor:
            assert (await cursor.fetchone())["status"] == "pending"


@pytest.mark.asyncio
async def test_act_corpus_json_replacement_requires_sync(runtime_sandbox):
    source = runtime_sandbox["root"] / "export"
    write_pair(source)
    await run_sync(source)

    async with aiosqlite.connect(runtime_sandbox["db_path"]) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT id FROM documents LIMIT 1") as cursor:
            document_id = (await cursor.fetchone())["id"]

        replacement = UploadFile(
            filename="replacement.json",
            file=io.BytesIO(sample_document().encode()),
        )
        with pytest.raises(HTTPException) as error:
            await replace_json(document_id, replacement, db)

    assert error.value.status_code == 409
    assert "backend.sync_acts" in error.value.detail
