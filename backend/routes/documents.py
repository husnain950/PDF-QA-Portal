import os
import tempfile
import uuid
from datetime import datetime

import aiosqlite
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from backend.database import get_db
from backend.models import DocumentResponse, DocumentStats
from backend.runtime import UPLOAD_DIR
from backend.services.document_store import (
    ReviewConflict,
    apply_parsed_document,
    document_status,
)
from backend.services.json_parser import parse_json_document
from backend.services.pdf_service import get_pdf_page_count

router = APIRouter(prefix="/documents", tags=["documents"])

def get_upload_path(filename: str) -> str:
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    return os.path.join(UPLOAD_DIR, filename)

def safe_upload_name(filename: str | None, fallback: str) -> str:
    cleaned = os.path.basename(filename or "").replace("\x00", "")
    return cleaned or fallback

@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    pdf: UploadFile = File(...),
    json_file: UploadFile = File(...),
    name: str = Form(...),
    db: aiosqlite.Connection = Depends(get_db)
):
    # Validate file formats
    if not (pdf.filename or "").lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="PDF file must have .pdf extension")
    if not (json_file.filename or "").lower().endswith(".json"):
        raise HTTPException(status_code=400, detail="JSON file must have .json extension")

    doc_id = str(uuid.uuid4())
    pdf_filename = f"{doc_id}_{safe_upload_name(pdf.filename, 'document.pdf')}"
    json_filename = f"{doc_id}_{safe_upload_name(json_file.filename, 'document.json')}"

    pdf_path = get_upload_path(pdf_filename)
    json_path = get_upload_path(json_filename)

    # Save PDF
    try:
        with open(pdf_path, "wb") as f:
            f.write(await pdf.read())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save PDF file: {e}")

    # Save JSON
    try:
        json_content_bytes = await json_file.read()
        with open(json_path, "wb") as f:
            f.write(json_content_bytes)
        json_content = json_content_bytes.decode("utf-8")
    except Exception as e:
        # Clean up PDF if JSON save fails
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
        raise HTTPException(status_code=500, detail=f"Failed to save JSON file: {e}")

    # Get page count
    total_pages = get_pdf_page_count(pdf_path)
    if total_pages == 0:
        # Clean up files
        os.remove(pdf_path)
        os.remove(json_path)
        raise HTTPException(status_code=400, detail="Failed to read pages from PDF file")

    # Parse JSON sections and footnotes
    try:
        sections, footnotes = parse_json_document(json_content, document_id=doc_id)
    except Exception as e:
        os.remove(pdf_path)
        os.remove(json_path)
        raise HTTPException(status_code=400, detail=f"Failed to parse JSON document: {e}")

    total_sections = len(sections)
    uploaded_at = datetime.utcnow().isoformat() + "Z"

    # Insert into DB
    try:
        # Insert document
        await db.execute(
            """
            INSERT INTO documents (
                id, name, pdf_filename, json_filename, total_sections,
                total_pages, uploaded_at, status, source_type, source_key,
                source_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                doc_id,
                name,
                pdf_filename,
                json_filename,
                total_sections,
                total_pages,
                uploaded_at,
                "pending",
                "upload",
                None,
                None,
            ),
        )

        # Insert sections
        for sec in sections:
            await db.execute(
                """
                INSERT INTO sections (
                    id, document_id, chapter_code, chapter_heading, part_code, part_heading,
                    division_code, division_heading, section_code, section_heading,
                    start_page, end_page, html_content, plain_text, sort_order,
                    review_status, source_key
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    sec["id"], doc_id, sec["chapter_code"], sec["chapter_heading"],
                    sec["part_code"], sec["part_heading"], sec["division_code"], sec["division_heading"],
                    sec["section_code"], sec["section_heading"], sec["start_page"], sec["end_page"],
                    sec["html_content"], sec["plain_text"], sec["sort_order"],
                    sec["review_status"], sec["source_key"]
                )
            )

        # Insert footnotes
        for fn in footnotes:
            await db.execute(
                """
                INSERT INTO footnotes (id, section_id, marker, page, text, html_content, review_status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (fn["id"], fn["section_id"], fn["marker"], fn["page"], fn["text"], fn.get("html_content", ""), fn["review_status"])
            )

        await db.commit()
    except Exception as e:
        await db.rollback()
        # Clean up files
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
        if os.path.exists(json_path):
            os.remove(json_path)
        raise HTTPException(status_code=500, detail=f"Database write failed: {e}")

    return DocumentResponse(
        id=doc_id,
        name=name,
        pdf_filename=pdf_filename,
        json_filename=json_filename,
        total_sections=total_sections,
        total_pages=total_pages,
        uploaded_at=uploaded_at,
        status="pending",
        source_type="upload",
        source_key=None,
        stats=DocumentStats(reviewed=0, approved=0, has_issues=0, pending=total_sections)
    )

@router.get("", response_model=list[DocumentResponse])
async def list_documents(db: aiosqlite.Connection = Depends(get_db)):
    query = """
        SELECT 
            d.id, d.name, d.pdf_filename, d.json_filename, d.total_sections,
            d.total_pages, d.uploaded_at, d.status, d.source_type, d.source_key,
            COUNT(CASE WHEN s.review_status != 'pending' THEN 1 END) as reviewed,
            COUNT(CASE WHEN s.review_status = 'approved' THEN 1 END) as approved,
            COUNT(CASE WHEN s.review_status = 'has_issues' THEN 1 END) as has_issues,
            COUNT(CASE WHEN s.review_status = 'pending' THEN 1 END) as pending
        FROM documents d
        LEFT JOIN sections s ON s.document_id = d.id
        GROUP BY d.id
        ORDER BY d.uploaded_at DESC
    """
    async with db.execute(query) as cursor:
        rows = await cursor.fetchall()
        
    results = []
    for r in rows:
        results.append(DocumentResponse(
            id=r["id"],
            name=r["name"],
            pdf_filename=r["pdf_filename"],
            json_filename=r["json_filename"],
            total_sections=r["total_sections"],
            total_pages=r["total_pages"],
            uploaded_at=r["uploaded_at"],
            status=r["status"],
            source_type=r["source_type"],
            source_key=r["source_key"],
            stats=DocumentStats(
                reviewed=r["reviewed"],
                approved=r["approved"],
                has_issues=r["has_issues"],
                pending=r["pending"]
            )
        ))
    return results

@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(document_id: str, db: aiosqlite.Connection = Depends(get_db)):
    query = """
        SELECT 
            d.id, d.name, d.pdf_filename, d.json_filename, d.total_sections,
            d.total_pages, d.uploaded_at, d.status, d.source_type, d.source_key,
            COUNT(CASE WHEN s.review_status != 'pending' THEN 1 END) as reviewed,
            COUNT(CASE WHEN s.review_status = 'approved' THEN 1 END) as approved,
            COUNT(CASE WHEN s.review_status = 'has_issues' THEN 1 END) as has_issues,
            COUNT(CASE WHEN s.review_status = 'pending' THEN 1 END) as pending
        FROM documents d
        LEFT JOIN sections s ON s.document_id = d.id
        WHERE d.id = ?
        GROUP BY d.id
    """
    async with db.execute(query, (document_id,)) as cursor:
        r = await cursor.fetchone()
        
    if not r:
        raise HTTPException(status_code=404, detail="Document not found")
        
    return DocumentResponse(
        id=r["id"],
        name=r["name"],
        pdf_filename=r["pdf_filename"],
        json_filename=r["json_filename"],
        total_sections=r["total_sections"],
        total_pages=r["total_pages"],
        uploaded_at=r["uploaded_at"],
        status=r["status"],
        source_type=r["source_type"],
        source_key=r["source_key"],
        stats=DocumentStats(
            reviewed=r["reviewed"],
            approved=r["approved"],
            has_issues=r["has_issues"],
            pending=r["pending"]
        )
    )

@router.get("/{document_id}/raw-files")
async def get_raw_files(document_id: str, db: aiosqlite.Connection = Depends(get_db)):
    async with db.execute("SELECT pdf_filename, json_filename FROM documents WHERE id = ?", (document_id,)) as cursor:
        r = await cursor.fetchone()
    if not r:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"pdf_filename": r["pdf_filename"], "json_filename": r["json_filename"]}

@router.delete("/{document_id}")
async def delete_document(document_id: str, db: aiosqlite.Connection = Depends(get_db)):
    # Find files to delete
    async with db.execute("SELECT pdf_filename, json_filename FROM documents WHERE id = ?", (document_id,)) as cursor:
        r = await cursor.fetchone()
    if not r:
        raise HTTPException(status_code=404, detail="Document not found")

    pdf_filename, json_filename = r["pdf_filename"], r["json_filename"]
    pdf_path = get_upload_path(pdf_filename)
    json_path = get_upload_path(json_filename)

    # Delete from DB (ON DELETE CASCADE will delete sections, footnotes, annotations)
    try:
        await db.execute("PRAGMA foreign_keys = ON;")
        await db.execute("DELETE FROM documents WHERE id = ?", (document_id,))
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Database deletion failed: {e}")

    # Delete files from disk
    if os.path.exists(pdf_path):
        try:
            os.remove(pdf_path)
        except Exception as e:
            print(f"Error removing PDF file: {e}")
            
    if os.path.exists(json_path):
        try:
            os.remove(json_path)
        except Exception as e:
            print(f"Error removing JSON file: {e}")

    return JSONResponse(content={"message": "Document and all associated data deleted successfully"})

@router.post("/{document_id}/replace-json", response_model=DocumentResponse)
async def replace_json(
    document_id: str,
    json_file: UploadFile = File(...),
    db: aiosqlite.Connection = Depends(get_db)
):
    if not (json_file.filename or "").lower().endswith(".json"):
        raise HTTPException(status_code=400, detail="JSON file must have .json extension")

    async with db.execute(
        """
        SELECT name, pdf_filename, json_filename, total_pages, uploaded_at,
               source_type, source_key
        FROM documents
        WHERE id = ?
        """,
        (document_id,),
    ) as cursor:
        r = await cursor.fetchone()
    if not r:
        raise HTTPException(status_code=404, detail="Document not found")
    if r["source_type"] == "acts_corpus":
        raise HTTPException(
            status_code=409,
            detail=(
                "ACT Corpus documents are managed by backend.sync_acts; "
                "update the canonical export and run the sync command instead."
            ),
        )

    try:
        json_content_bytes = await json_file.read()
        json_content = json_content_bytes.decode("utf-8")
        sections, footnotes = parse_json_document(
            json_content,
            document_id=document_id,
        )
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to parse JSON document: {e}",
        )

    json_path = get_upload_path(r["json_filename"])
    previous_bytes = None
    if os.path.exists(json_path):
        with open(json_path, "rb") as existing_file:
            previous_bytes = existing_file.read()

    os.makedirs(os.path.dirname(json_path), exist_ok=True)
    with tempfile.NamedTemporaryFile(
        dir=os.path.dirname(json_path),
        prefix=".replace-",
        suffix=".json",
        delete=False,
    ) as staged:
        staged.write(json_content_bytes)
        staged_path = staged.name

    replaced_runtime_file = False
    try:
        await db.execute("PRAGMA foreign_keys = ON;")
        stats = await apply_parsed_document(
            db,
            document_id,
            sections,
            footnotes,
        )
        doc_status = document_status(stats)
        await db.execute(
            "UPDATE documents SET total_sections = ?, status = ? WHERE id = ?",
            (stats["total"], doc_status, document_id),
        )
        os.replace(staged_path, json_path)
        replaced_runtime_file = True
        await db.commit()
    except ReviewConflict as conflict:
        await db.rollback()
        if os.path.exists(staged_path):
            os.remove(staged_path)
        raise HTTPException(status_code=409, detail=str(conflict))
    except Exception as e:
        await db.rollback()
        if os.path.exists(staged_path):
            os.remove(staged_path)
        if previous_bytes is not None:
            with open(json_path, "wb") as previous_file:
                previous_file.write(previous_bytes)
        elif replaced_runtime_file and os.path.exists(json_path):
            os.remove(json_path)
        raise HTTPException(status_code=500, detail=f"Database update failed: {e}")

    return DocumentResponse(
        id=document_id,
        name=r["name"],
        pdf_filename=r["pdf_filename"],
        json_filename=r["json_filename"],
        total_sections=stats["total"],
        total_pages=r["total_pages"],
        uploaded_at=r["uploaded_at"],
        status=doc_status,
        source_type=r["source_type"],
        source_key=r["source_key"],
        stats=DocumentStats(
            reviewed=stats["reviewed"],
            approved=stats["approved"],
            has_issues=stats["has_issues"],
            pending=stats["pending"],
        )
    )
