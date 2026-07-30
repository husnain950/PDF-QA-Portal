import json
import uuid
from typing import Any, Dict, List, Optional, Tuple


def _stable_id(document_id: Optional[str], source_key: str) -> str:
    if not document_id:
        return str(uuid.uuid4())
    return str(
        uuid.uuid5(
            uuid.NAMESPACE_URL,
            f"pdf-qa-portal:{document_id}:{source_key}",
        )
    )


def parse_json_document(
    json_content: str,
    document_id: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Flatten the enriched legal JSON into page-addressable review units.

    ``source_key`` is a stable JSON-pointer-style path. It deliberately does not
    use legal section codes because those codes repeat heavily in schedules and
    amendment Acts.
    """

    data = json.loads(json_content)
    sections: List[Dict[str, Any]] = []
    footnotes: List[Dict[str, Any]] = []
    sort_order = 0

    def process_section(
        sec_data: Dict[str, Any],
        context: Dict[str, Any],
        source_key: str,
    ) -> None:
        nonlocal sort_order

        section_id = _stable_id(document_id, source_key)
        start_page = sec_data.get("start_page") or sec_data.get("page_number")
        end_page = sec_data.get("end_page") or start_page

        sec_row = {
            "id": section_id,
            "source_key": source_key,
            "chapter_code": context.get("chapter_code"),
            "chapter_heading": context.get("chapter_heading"),
            "part_code": context.get("part_code"),
            "part_heading": context.get("part_heading"),
            "division_code": context.get("division_code"),
            "division_heading": context.get("division_heading"),
            "section_code": str(sec_data.get("code") or ""),
            "section_heading": str(sec_data.get("heading") or ""),
            "start_page": start_page,
            "end_page": end_page,
            "html_content": sec_data.get("html", ""),
            "plain_text": sec_data.get("plain_text", ""),
            "sort_order": sort_order,
            "review_status": "pending",
        }
        sections.append(sec_row)
        sort_order += 1

        for index, footnote in enumerate(sec_data.get("footnotes") or []):
            if not isinstance(footnote, dict):
                continue
            footnote_key = f"{source_key}/footnotes/{index}"
            footnotes.append(
                {
                    "id": _stable_id(document_id, footnote_key),
                    "source_key": footnote_key,
                    "section_id": section_id,
                    "marker": footnote.get("marker", ""),
                    "page": footnote.get("page") or start_page,
                    "text": footnote.get("text", ""),
                    "html_content": footnote.get("html", ""),
                    "review_status": "pending",
                }
            )

    def process_container(
        node: Dict[str, Any],
        context: Dict[str, Any],
        source_key: str,
        kind: str,
        allow_content_leaf: bool,
    ) -> None:
        next_context = context.copy()
        code = node.get("code")
        heading = node.get("heading")

        if kind == "chapter" or kind == "schedule":
            next_context.update(
                chapter_code=code,
                chapter_heading=heading,
                part_code=None,
                part_heading=None,
                division_code=None,
                division_heading=None,
            )
        elif kind == "part":
            next_context.update(
                part_code=code,
                part_heading=heading,
                division_code=None,
                division_heading=None,
            )
        elif kind == "division":
            next_context.update(
                division_code=code,
                division_heading=heading,
            )

        child_collections = ("sections", "parts", "divisions")
        has_children = any(node.get(key) for key in child_collections)
        if allow_content_leaf and "html" in node and not has_children:
            process_section(node, next_context, source_key)

        # Keep the portal's established reading order: direct sections first,
        # followed by parts and divisions.
        for index, section in enumerate(node.get("sections") or []):
            if isinstance(section, dict):
                process_section(
                    section,
                    next_context,
                    f"{source_key}/sections/{index}",
                )

        for index, part in enumerate(node.get("parts") or []):
            if isinstance(part, dict):
                process_container(
                    part,
                    next_context,
                    f"{source_key}/parts/{index}",
                    "part",
                    allow_content_leaf=kind == "schedule" or allow_content_leaf,
                )

        for index, division in enumerate(node.get("divisions") or []):
            if isinstance(division, dict):
                process_container(
                    division,
                    next_context,
                    f"{source_key}/divisions/{index}",
                    "division",
                    allow_content_leaf=kind == "schedule" or allow_content_leaf,
                )

    empty_context = {
        "chapter_code": None,
        "chapter_heading": None,
        "part_code": None,
        "part_heading": None,
        "division_code": None,
        "division_heading": None,
    }

    for index, chapter in enumerate(data.get("chapters") or []):
        if isinstance(chapter, dict):
            process_container(
                chapter,
                empty_context,
                f"/chapters/{index}",
                "chapter",
                allow_content_leaf=False,
            )

    for index, schedule in enumerate(data.get("schedules") or []):
        if isinstance(schedule, dict):
            process_container(
                schedule,
                empty_context,
                f"/schedules/{index}",
                "schedule",
                allow_content_leaf=False,
            )

    return sections, footnotes
