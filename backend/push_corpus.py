"""Push a local corpus into a *deployed* portal over its own HTTP API.

A deployment has no source PDFs of its own -- they are not in git, and the pipeline
repositories are not on the server -- so ``sync_acts`` cannot run there. This walks the
local database and re-uploads each document to a remote instance instead.

Smallest first, so most of the corpus is visible early and the few large PDFs (the ones
that might exhaust a small container) are attempted last. Documents already present by
name are skipped, so it is safe to re-run and safe to resume after an interruption.

    python -m backend.push_corpus --base-url https://your-portal.example.com
    python -m backend.push_corpus --base-url ... --dry-run

Note this creates ``source_type='upload'`` documents: deterministic corpus ids and
pipeline health metrics come from ``sync_acts``, which needs the pipeline repositories.
Where the server can see them, prefer that.
"""

import argparse
import json
import mimetypes
import os
import sqlite3
import sys
import time
import urllib.error
import urllib.request
import uuid

from backend.database import DB_PATH as DB
from backend.services.blob_store import upload_root

UPLOADS = upload_root()
BASE = ""


def multipart(fields, files):
    boundary = uuid.uuid4().hex
    body = bytearray()
    for name, value in fields.items():
        body += f"--{boundary}\r\n".encode()
        body += f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode()
        body += value.encode() + b"\r\n"
    for name, (filename, path) in files.items():
        ctype = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        body += f"--{boundary}\r\n".encode()
        body += (
            f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'
        ).encode()
        body += f"Content-Type: {ctype}\r\n\r\n".encode()
        with open(path, "rb") as handle:
            body += handle.read()
        body += b"\r\n"
    body += f"--{boundary}--\r\n".encode()
    return bytes(body), f"multipart/form-data; boundary={boundary}"


def existing_names():
    request = urllib.request.Request(f"{BASE}/api/documents")
    with urllib.request.urlopen(request, timeout=120) as response:
        return {doc["name"] for doc in json.load(response)}


def main():
    global BASE
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base-url", required=True, help="deployed portal root URL")
    parser.add_argument(
        "--dry-run", action="store_true", help="list what would be sent, send nothing"
    )
    args = parser.parse_args()
    BASE = args.base_url.rstrip("/")

    connection = sqlite3.connect(DB)
    connection.row_factory = sqlite3.Row
    todo = []
    for row in connection.execute(
        "SELECT name, pdf_filename, json_filename FROM documents"
    ):
        pdf = os.path.join(UPLOADS, row["pdf_filename"])
        js = os.path.join(UPLOADS, row["json_filename"])
        if os.path.exists(pdf) and os.path.exists(js):
            size = os.path.getsize(pdf) + os.path.getsize(js)
            todo.append((size, row["name"], pdf, js))
    todo.sort()

    present = existing_names()
    total_bytes = sum(s for s, n, _, _ in todo if n not in present)
    print(
        f"{len(todo)} local documents, {len(present)} already on production, "
        f"{total_bytes / 1048576:.0f} MB to send",
        flush=True,
    )

    if args.dry_run:
        for size, name, _pdf, _js in todo:
            if name not in present:
                print(f"  would send {size / 1048576:6.1f} MB  {name}")
        return 0

    done = failed = 0
    sent = 0
    started = time.time()
    for size, name, pdf, js in todo:
        if name in present:
            continue
        body, ctype = multipart(
            {"name": name},
            {
                "pdf": (os.path.basename(pdf), pdf),
                "json_file": (os.path.basename(js), js),
            },
        )
        request = urllib.request.Request(
            f"{BASE}/api/documents/upload", data=body, method="POST"
        )
        request.add_header("Content-Type", ctype)
        for attempt in (1, 2):
            try:
                with urllib.request.urlopen(request, timeout=900) as response:
                    json.load(response)
                done += 1
                sent += size
                elapsed = time.time() - started
                print(
                    f"  [{done:3d}/{len(todo) - len(present)}] "
                    f"{size / 1048576:6.1f} MB  {sent / 1048576:6.0f} MB sent  "
                    f"{elapsed / 60:4.1f} min  {name[:48]}",
                    flush=True,
                )
                break
            except Exception as error:
                if attempt == 2:
                    failed += 1
                    detail = getattr(error, "read", lambda: b"")()[:200]
                    print(
                        f"  FAILED {name[:48]}: {error} {detail!r}",
                        file=sys.stderr,
                        flush=True,
                    )
                else:
                    time.sleep(5)

    print(
        f"\ndone: {done} uploaded, {failed} failed, "
        f"{(time.time() - started) / 60:.1f} min",
        flush=True,
    )
    print(f"{BASE} now has {len(existing_names())} documents", flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
