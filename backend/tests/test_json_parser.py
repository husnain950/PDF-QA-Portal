import json

from backend.services.json_parser import parse_json_document
from backend.tests.conftest import sample_document


def test_source_keys_and_ids_are_stable_despite_repeated_legal_codes():
    first_sections, first_footnotes = parse_json_document(
        sample_document(),
        document_id="document-1",
    )
    second_sections, second_footnotes = parse_json_document(
        sample_document(),
        document_id="document-1",
    )

    assert [section["section_code"] for section in first_sections] == ["1", "1"]
    assert [section["source_key"] for section in first_sections] == [
        "/chapters/0/sections/0",
        "/chapters/0/sections/1",
    ]
    assert len({section["source_key"] for section in first_sections}) == 2
    assert [section["id"] for section in first_sections] == [
        section["id"] for section in second_sections
    ]
    assert [footnote["id"] for footnote in first_footnotes] == [
        footnote["id"] for footnote in second_footnotes
    ]


def test_json_pointer_escaping_handles_container_names_safely():
    payload = json.loads(sample_document())
    payload["chapters"][0]["code"] = "I/~"
    sections, _ = parse_json_document(json.dumps(payload), document_id="document-1")

    # Array position, not a legal label, defines identity.
    assert sections[0]["source_key"] == "/chapters/0/sections/0"
