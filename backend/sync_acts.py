"""Repeatably import the Acts-Discovery export corpus into runtime storage."""

import argparse
import asyncio
import hashlib
import json
import os
import shutil
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

import aiosqlite

from backend.database import DB_PATH
from backend.runtime import UPLOAD_DIR, bootstrap_runtime
from backend.services.document_store import (
    ReviewConflict,
    apply_parsed_document,
    document_status,
)
from backend.services.json_parser import parse_json_document
from backend.services.pdf_service import get_pdf_page_count

SOURCE_TYPE = "acts_corpus"


@dataclass(frozen=True)
class ExportPair:
    source_key: str
    pdf_path: Path
    json_path: Path


@dataclass
class ValidatedPair:
    pair: ExportPair
    document_id: str
    source_hash: str
    pdf_hash: str
    json_hash: str
    total_pages: int
    sections: List[dict]
    footnotes: List[dict]


def discover_pairs(source: Path) -> List[ExportPair]:
    source = source.expanduser().resolve()
    if not source.is_dir():
        raise ValueError(f"Source directory does not exist: {source}")

    pairs: List[ExportPair] = []
    failures: List[str] = []
    for directory in sorted(source.iterdir(), key=lambda item: item.name.casefold()):
        if not directory.is_dir():
            continue
        if directory.is_symlink():
            failures.append(f"{directory.name}: symbolic-link directories are not allowed")
            continue
        pdfs = sorted(directory.glob("*.pdf"), key=lambda item: item.name.casefold())
        json_files = sorted(
            directory.glob("*.json"),
            key=lambda item: item.name.casefold(),
        )
        if len(pdfs) != 1 or len(json_files) != 1:
            failures.append(
                f"{directory.name}: expected one PDF and one JSON "
                f"(found {len(pdfs)} PDF, {len(json_files)} JSON)"
            )
            continue
        if pdfs[0].is_symlink() or json_files[0].is_symlink():
            failures.append(f"{directory.name}: symbolic-link source files are not allowed")
            continue
        pairs.append(
            ExportPair(
                source_key=directory.name,
                pdf_path=pdfs[0].resolve(),
                json_path=json_files[0].resolve(),
            )
        )

    if failures:
        raise ValueError("; ".join(failures))
    if not pairs:
        raise ValueError(f"No complete export pairs found in {source}")
    return pairs


def hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def deterministic_document_id(source_key: str) -> str:
    return str(
        uuid.uuid5(
            uuid.NAMESPACE_URL,
            f"pdf-qa-portal:{SOURCE_TYPE}:{source_key}",
        )
    )


def validate_pair(pair: ExportPair) -> ValidatedPair:
    document_id = deterministic_document_id(pair.source_key)
    json_content = pair.json_path.read_text(encoding="utf-8")
    sections, footnotes = parse_json_document(
        json_content,
        document_id=document_id,
    )
    if not sections:
        raise ValueError(f"{pair.source_key}: JSON has no reviewable sections")

    total_pages = get_pdf_page_count(str(pair.pdf_path))
    if total_pages < 1:
        raise ValueError(f"{pair.source_key}: PDF has no readable pages")

    source_keys = [section["source_key"] for section in sections]
    if len(source_keys) != len(set(source_keys)):
        raise ValueError(f"{pair.source_key}: duplicate section source keys")

    for section in sections:
        start = section.get("start_page")
        end = section.get("end_page")
        if not isinstance(start, int) or not isinstance(end, int):
            raise ValueError(
                f"{pair.source_key}: {section['source_key']} has no integer page range"
            )
        if start < 1 or end < start or end > total_pages:
            raise ValueError(
                f"{pair.source_key}: {section['source_key']} has invalid "
                f"page range {start}-{end} for {total_pages} pages"
            )

    pdf_hash = hash_file(pair.pdf_path)
    json_hash = hash_file(pair.json_path)
    source_hash = hashlib.sha256(
        f"{pdf_hash}:{json_hash}".encode("ascii")
    ).hexdigest()
    return ValidatedPair(
        pair=pair,
        document_id=document_id,
        source_hash=source_hash,
        pdf_hash=pdf_hash,
        json_hash=json_hash,
        total_pages=total_pages,
        sections=sections,
        footnotes=footnotes,
    )


def runtime_filename(document_id: str, digest: str, source_name: str) -> str:
    safe_name = os.path.basename(source_name).replace("\x00", "")
    return f"{document_id}_{digest[:16]}_{safe_name}"


def copy_if_missing(source: Path, destination: Path) -> bool:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        return False
    temporary = destination.with_name(f".{destination.name}.syncing")
    if temporary.exists():
        temporary.unlink()
    shutil.copy2(source, temporary)
    os.replace(temporary, destination)
    return True


async def file_is_referenced(
    db: aiosqlite.Connection,
    filename: str,
) -> bool:
    async with db.execute(
        """
        SELECT 1
        FROM documents
        WHERE pdf_filename = ? OR json_filename = ?
        LIMIT 1
        """,
        (filename, filename),
    ) as cursor:
        return await cursor.fetchone() is not None


async def sync_validated_pair(
    db: aiosqlite.Connection,
    validated: ValidatedPair,
) -> str:
    pair = validated.pair
    async with db.execute(
        """
        SELECT *
        FROM documents
        WHERE source_type = ? AND source_key = ?
        """,
        (SOURCE_TYPE, pair.source_key),
    ) as cursor:
        existing_row = await cursor.fetchone()
    existing = dict(existing_row) if existing_row else None

    document_id = existing["id"] if existing else validated.document_id
    if document_id != validated.document_id:
        # Recreate stable child ids with the already-established document id.
        sections, footnotes = parse_json_document(
            pair.json_path.read_text(encoding="utf-8"),
            document_id=document_id,
        )
        validated.sections = sections
        validated.footnotes = footnotes

    pdf_filename = runtime_filename(
        document_id,
        validated.pdf_hash,
        pair.pdf_path.name,
    )
    json_filename = runtime_filename(
        document_id,
        validated.json_hash,
        pair.json_path.name,
    )
    pdf_destination = Path(UPLOAD_DIR) / pdf_filename
    json_destination = Path(UPLOAD_DIR) / json_filename

    if (
        existing
        and existing.get("source_hash") == validated.source_hash
        and pdf_destination.exists()
        and json_destination.exists()
    ):
        return "skipped"

    created_files: List[Path] = []
    if copy_if_missing(pair.pdf_path, pdf_destination):
        created_files.append(pdf_destination)
    if copy_if_missing(pair.json_path, json_destination):
        created_files.append(json_destination)

    old_files = []
    if existing:
        old_files = [
            existing["pdf_filename"],
            existing["json_filename"],
        ]

    try:
        await db.execute("BEGIN IMMEDIATE")
        uploaded_at = (
            existing["uploaded_at"]
            if existing
            else datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        )
        if existing:
            await db.execute(
                """
                UPDATE documents SET
                    name = ?, pdf_filename = ?, json_filename = ?,
                    total_pages = ?, source_hash = ?
                WHERE id = ?
                """,
                (
                    pair.source_key,
                    pdf_filename,
                    json_filename,
                    validated.total_pages,
                    validated.source_hash,
                    document_id,
                ),
            )
        else:
            await db.execute(
                """
                INSERT INTO documents (
                    id, name, pdf_filename, json_filename, total_sections,
                    total_pages, uploaded_at, status, source_type, source_key,
                    source_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    document_id,
                    pair.source_key,
                    pdf_filename,
                    json_filename,
                    len(validated.sections),
                    validated.total_pages,
                    uploaded_at,
                    "pending",
                    SOURCE_TYPE,
                    pair.source_key,
                    validated.source_hash,
                ),
            )

        stats = await apply_parsed_document(
            db,
            document_id,
            validated.sections,
            validated.footnotes,
        )
        await db.execute(
            """
            UPDATE documents
            SET total_sections = ?, status = ?
            WHERE id = ?
            """,
            (stats["total"], document_status(stats), document_id),
        )
        await db.commit()
    except Exception:
        await db.rollback()
        for path in created_files:
            if path.exists():
                path.unlink()
        raise

    for filename in old_files:
        if filename not in (pdf_filename, json_filename):
            path = Path(UPLOAD_DIR) / filename
            if path.exists() and not await file_is_referenced(db, filename):
                path.unlink()
    return "updated" if existing else "added"


async def run_sync(source: Path, dry_run: bool = False) -> Dict[str, int]:
    pairs = discover_pairs(source)
    summary = {
        "discovered": len(pairs),
        "validated": 0,
        "added": 0,
        "updated": 0,
        "skipped": 0,
        "failed": 0,
        "sections": 0,
        "footnotes": 0,
        "pdf_pages": 0,
    }

    validated_pairs: List[ValidatedPair] = []
    for pair in pairs:
        try:
            validated = validate_pair(pair)
            validated_pairs.append(validated)
            summary["validated"] += 1
            summary["sections"] += len(validated.sections)
            summary["footnotes"] += len(validated.footnotes)
            summary["pdf_pages"] += validated.total_pages
        except Exception as error:
            summary["failed"] += 1
            print(f"ERROR {pair.source_key}: {error}", file=sys.stderr)

    if dry_run or summary["failed"]:
        return summary

    await bootstrap_runtime()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA foreign_keys = ON;")
        for validated in validated_pairs:
            try:
                result = await sync_validated_pair(db, validated)
                summary[result] += 1
            except ReviewConflict as conflict:
                summary["failed"] += 1
                print(
                    f"CONFLICT {validated.pair.source_key}: {conflict}",
                    file=sys.stderr,
                )
            except Exception as error:
                summary["failed"] += 1
                print(
                    f"ERROR {validated.pair.source_key}: {error}",
                    file=sys.stderr,
                )
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Sync Acts-Discovery PDF/JSON exports into PDF-QA Portal",
    )
    parser.add_argument(
        "--source",
        required=True,
        type=Path,
        help="Directory containing one folder per exported Act or edition",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate the complete corpus without writing files or database rows",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        summary = asyncio.run(run_sync(args.source, dry_run=args.dry_run))
    except Exception as error:
        print(f"Sync failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 1 if summary["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
