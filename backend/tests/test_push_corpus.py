"""The multipart encoder used to re-seed a deployed portal over its HTTP API."""

from email import message_from_bytes

from backend import push_corpus


def _parts(body: bytes, content_type: str):
    """Decode with the stdlib email parser (``cgi`` is gone in 3.13)."""
    message = message_from_bytes(
        b"Content-Type: " + content_type.encode() + b"\r\nMIME-Version: 1.0\r\n\r\n" + body
    )
    assert message.is_multipart(), "encoder did not produce a parseable multipart body"
    found = {}
    for part in message.get_payload():
        disposition = part.get("Content-Disposition", "")
        name = part.get_param("name", header="Content-Disposition")
        found[name] = {
            "value": part.get_payload(decode=True),
            "filename": part.get_filename(),
            "type": part.get_content_type(),
            "disposition": disposition,
        }
    return found


def test_multipart_round_trips_fields_and_binary_files(tmp_path):
    pdf = tmp_path / "act.pdf"
    # Bytes that would corrupt if the encoder ever treated the body as text, including
    # a line that looks like a boundary delimiter.
    raw = b"%PDF-1.4\r\n\x00\xff\xfe binary \r\n--not-a-boundary--\r\n"
    pdf.write_bytes(raw)
    js = tmp_path / "act.json"
    js.write_text('{"metadata": {"total_pages": 1}}', encoding="utf-8")

    body, content_type = push_corpus.multipart(
        {"name": "Customs Act, 1969 — 30.06.2025"},
        {"pdf": ("act.pdf", str(pdf)), "json_file": ("act.json", str(js))},
    )
    assert content_type.startswith("multipart/form-data; boundary=")

    parts = _parts(body, content_type)
    assert set(parts) == {"name", "pdf", "json_file"}
    assert parts["name"]["value"].decode("utf-8") == "Customs Act, 1969 — 30.06.2025"
    assert parts["pdf"]["filename"] == "act.pdf"
    assert parts["pdf"]["value"] == raw, "binary must survive verbatim"
    assert parts["pdf"]["type"] == "application/pdf"
    assert parts["json_file"]["value"] == js.read_bytes()
    assert parts["json_file"]["type"] == "application/json"


def test_multipart_uses_a_fresh_boundary_each_call(tmp_path):
    pdf = tmp_path / "a.pdf"
    pdf.write_bytes(b"%PDF-1.4 x")
    files = {"pdf": ("a.pdf", str(pdf))}
    _, first = push_corpus.multipart({"name": "a"}, files)
    _, second = push_corpus.multipart({"name": "a"}, files)
    assert first != second
