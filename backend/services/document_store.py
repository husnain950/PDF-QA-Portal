from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

import aiosqlite


@dataclass
class ReviewConflict(Exception):
    details: List[str]

    def __str__(self) -> str:
        return "; ".join(self.details)


def _legacy_section_key(section: Dict[str, Any]) -> Tuple[Any, ...]:
    return (
        section.get("sort_order"),
        section.get("chapter_code") or "",
        section.get("part_code") or "",
        section.get("division_code") or "",
        section.get("section_code") or "",
    )


async def apply_parsed_document(
    db: aiosqlite.Connection,
    document_id: str,
    sections: List[Dict[str, Any]],
    footnotes: List[Dict[str, Any]],
) -> Dict[str, int]:
    """Upsert parsed content while preserving valid QA state.

    Stable source keys are the primary identity. Existing databases are
    backfilled once through a unique sort-order/hierarchy fallback.
    """

    async with db.execute(
        """
        SELECT
            s.*,
            COUNT(a.id) AS annotation_count
        FROM sections s
        LEFT JOIN annotations a ON a.section_id = s.id
        WHERE s.document_id = ?
        GROUP BY s.id
        """,
        (document_id,),
    ) as cursor:
        existing_sections = [dict(row) for row in await cursor.fetchall()]

    by_source_key = {
        row["source_key"]: row
        for row in existing_sections
        if row.get("source_key")
    }
    by_legacy_key = {
        _legacy_section_key(row): row for row in existing_sections
    }
    existing_section_ids = {row["id"] for row in existing_sections}

    resolved_sections: List[Tuple[Dict[str, Any], str, str]] = []
    parsed_to_final: Dict[str, str] = {}
    used_section_ids = set()
    conflicts: List[str] = []
    reset_sections = 0

    for section in sections:
        existing = by_source_key.get(section["source_key"])
        if existing is None:
            existing = by_legacy_key.get(_legacy_section_key(section))

        final_id = existing["id"] if existing else section["id"]
        review_status = existing["review_status"] if existing else "pending"

        if existing:
            content_changed = (
                (existing.get("html_content") or "")
                != (section.get("html_content") or "")
                or (existing.get("plain_text") or "")
                != (section.get("plain_text") or "")
            )
            if content_changed and existing["annotation_count"]:
                conflicts.append(
                    f"{section['source_key']} changed with "
                    f"{existing['annotation_count']} annotation(s)"
                )
            elif content_changed and review_status != "pending":
                review_status = "pending"
                reset_sections += 1

        parsed_to_final[section["id"]] = final_id
        used_section_ids.add(final_id)
        resolved_sections.append((section, final_id, review_status))

    removed_sections = [
        row for row in existing_sections if row["id"] not in used_section_ids
    ]
    for row in removed_sections:
        if row["review_status"] != "pending" or row["annotation_count"]:
            conflicts.append(
                f"{row.get('source_key') or row['id']} was removed with QA state"
            )

    async with db.execute(
        """
        SELECT
            f.*,
            COUNT(a.id) AS annotation_count
        FROM footnotes f
        JOIN sections s ON s.id = f.section_id
        LEFT JOIN annotations a ON a.footnote_id = f.id
        WHERE s.document_id = ?
        GROUP BY f.id
        """,
        (document_id,),
    ) as cursor:
        existing_footnotes = [dict(row) for row in await cursor.fetchall()]

    footnotes_by_key = {
        (row["section_id"], row["marker"]): row
        for row in existing_footnotes
    }
    resolved_footnotes: List[Tuple[Dict[str, Any], str, str, str]] = []
    used_footnote_ids = set()

    for footnote in footnotes:
        final_section_id = parsed_to_final.get(footnote["section_id"])
        if not final_section_id:
            continue
        existing = footnotes_by_key.get(
            (final_section_id, footnote["marker"])
        )
        final_id = existing["id"] if existing else footnote["id"]
        review_status = existing["review_status"] if existing else "pending"

        if existing:
            content_changed = (
                (existing.get("text") or "") != (footnote.get("text") or "")
                or (existing.get("html_content") or "")
                != (footnote.get("html_content") or "")
            )
            if content_changed and existing["annotation_count"]:
                conflicts.append(
                    f"footnote {footnote['marker']} changed with annotation(s)"
                )
            elif content_changed and review_status != "pending":
                review_status = "pending"

        used_footnote_ids.add(final_id)
        resolved_footnotes.append(
            (footnote, final_id, final_section_id, review_status)
        )

    removed_footnotes = [
        row
        for row in existing_footnotes
        if row["id"] not in used_footnote_ids
    ]
    for row in removed_footnotes:
        if row["review_status"] != "pending" or row["annotation_count"]:
            conflicts.append(
                f"footnote {row['marker']} was removed with QA state"
            )

    if conflicts:
        raise ReviewConflict(conflicts)

    for section, final_id, review_status in resolved_sections:
        if final_id in existing_section_ids:
            await db.execute(
                """
                UPDATE sections SET
                    chapter_code = ?, chapter_heading = ?,
                    part_code = ?, part_heading = ?,
                    division_code = ?, division_heading = ?,
                    section_code = ?, section_heading = ?,
                    start_page = ?, end_page = ?,
                    html_content = ?, plain_text = ?,
                    sort_order = ?, review_status = ?, source_key = ?
                WHERE id = ?
                """,
                (
                    section["chapter_code"],
                    section["chapter_heading"],
                    section["part_code"],
                    section["part_heading"],
                    section["division_code"],
                    section["division_heading"],
                    section["section_code"],
                    section["section_heading"],
                    section["start_page"],
                    section["end_page"],
                    section["html_content"],
                    section["plain_text"],
                    section["sort_order"],
                    review_status,
                    section["source_key"],
                    final_id,
                ),
            )
        else:
            await db.execute(
                """
                INSERT INTO sections (
                    id, document_id, chapter_code, chapter_heading,
                    part_code, part_heading, division_code, division_heading,
                    section_code, section_heading, start_page, end_page,
                    html_content, plain_text, sort_order, review_status,
                    source_key
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    final_id,
                    document_id,
                    section["chapter_code"],
                    section["chapter_heading"],
                    section["part_code"],
                    section["part_heading"],
                    section["division_code"],
                    section["division_heading"],
                    section["section_code"],
                    section["section_heading"],
                    section["start_page"],
                    section["end_page"],
                    section["html_content"],
                    section["plain_text"],
                    section["sort_order"],
                    review_status,
                    section["source_key"],
                ),
            )

    existing_footnote_ids = {row["id"] for row in existing_footnotes}
    for footnote, final_id, final_section_id, review_status in resolved_footnotes:
        if final_id in existing_footnote_ids:
            await db.execute(
                """
                UPDATE footnotes SET
                    section_id = ?, marker = ?, page = ?, text = ?,
                    html_content = ?, review_status = ?
                WHERE id = ?
                """,
                (
                    final_section_id,
                    footnote["marker"],
                    footnote["page"],
                    footnote["text"],
                    footnote.get("html_content", ""),
                    review_status,
                    final_id,
                ),
            )
        else:
            await db.execute(
                """
                INSERT INTO footnotes (
                    id, section_id, marker, page, text, html_content,
                    review_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    final_id,
                    final_section_id,
                    footnote["marker"],
                    footnote["page"],
                    footnote["text"],
                    footnote.get("html_content", ""),
                    review_status,
                ),
            )

    for row in removed_footnotes:
        await db.execute("DELETE FROM footnotes WHERE id = ?", (row["id"],))
    for row in removed_sections:
        await db.execute("DELETE FROM sections WHERE id = ?", (row["id"],))

    async with db.execute(
        """
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN review_status = 'pending' THEN 1 ELSE 0 END) AS pending,
            SUM(CASE WHEN review_status = 'approved' THEN 1 ELSE 0 END) AS approved,
            SUM(CASE WHEN review_status = 'has_issues' THEN 1 ELSE 0 END) AS has_issues
        FROM sections
        WHERE document_id = ?
        """,
        (document_id,),
    ) as cursor:
        row = await cursor.fetchone()

    total = int(row["total"] or 0)
    pending = int(row["pending"] or 0)
    return {
        "total": total,
        "pending": pending,
        "approved": int(row["approved"] or 0),
        "has_issues": int(row["has_issues"] or 0),
        "reviewed": total - pending,
        "reset_sections": reset_sections,
    }


def document_status(stats: Dict[str, int]) -> str:
    if stats["total"] == 0 or stats["pending"] == stats["total"]:
        return "pending"
    if stats["pending"] == 0:
        return "completed"
    return "in_progress"
