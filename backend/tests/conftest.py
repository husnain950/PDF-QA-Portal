import json
from pathlib import Path

import pytest_asyncio
from pypdf import PdfWriter

import backend.database as database
import backend.runtime as runtime
import backend.sync_acts as sync_acts


def sample_document(*, second_text: str = "Second section") -> str:
    return json.dumps(
        {
            "metadata": {"total_pages": 3},
            "chapters": [
                {
                    "code": "I",
                    "heading": "General",
                    "sections": [
                        {
                            "code": "1",
                            "heading": "First",
                            "start_page": 1,
                            "end_page": 2,
                            "html": "<p>First section</p>",
                            "plain_text": "First section",
                            "footnotes": [
                                {
                                    "marker": "1",
                                    "page": 1,
                                    "text": "First footnote",
                                    "html": "<span>First footnote</span>",
                                }
                            ],
                        },
                        {
                            "code": "1",
                            "heading": "Repeated code",
                            "start_page": 3,
                            "end_page": 3,
                            "html": f"<p>{second_text}</p>",
                            "plain_text": second_text,
                            "footnotes": [],
                        },
                    ],
                }
            ],
            "schedules": [],
        }
    )


def write_pair(root: Path, name: str = "Test Act") -> Path:
    directory = root / name
    directory.mkdir(parents=True)
    writer = PdfWriter()
    for _ in range(3):
        writer.add_blank_page(width=612, height=792)
    with (directory / "act.pdf").open("wb") as target:
        writer.write(target)
    (directory / "act.json").write_text(sample_document(), encoding="utf-8")
    return directory


@pytest_asyncio.fixture
async def runtime_sandbox(monkeypatch, tmp_path):
    data_dir = tmp_path / "data"
    upload_dir = tmp_path / "uploads"
    db_path = data_dir / "qa_portal.db"
    missing_seed = tmp_path / "missing-seed.db"
    missing_uploads = tmp_path / "missing-seed-uploads"

    monkeypatch.setattr(database, "DB_DIR", str(data_dir))
    monkeypatch.setattr(database, "DB_PATH", str(db_path))
    monkeypatch.setattr(runtime, "DB_PATH", str(db_path))
    monkeypatch.setattr(runtime, "UPLOAD_DIR", str(upload_dir))
    monkeypatch.setattr(runtime, "SEED_DB_PATH", str(missing_seed))
    monkeypatch.setattr(runtime, "SEED_UPLOAD_DIR", str(missing_uploads))
    monkeypatch.setattr(sync_acts, "DB_PATH", str(db_path))
    monkeypatch.setattr(sync_acts, "UPLOAD_DIR", str(upload_dir))

    await database.init_db()
    return {
        "db_path": db_path,
        "upload_dir": upload_dir,
        "root": tmp_path,
    }
