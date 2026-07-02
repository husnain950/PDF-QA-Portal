import os
import uuid
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, status
from fastapi.responses import JSONResponse
import aiosqlite

from backend.database import get_db
from backend.models import DocumentResponse, DocumentStats
from backend.services.pdf_service import get_pdf_page_count
from backend.services.json_parser import parse_json_document

router = APIRouter(prefix="/documents", tags=["documents"])

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads")

def get_upload_path(filename: str) -> str:
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    return os.path.join(UPLOAD_DIR, filename)

@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    pdf: UploadFile = File(...),
    json_file: UploadFile = File(...),
    name: str = Form(...),
    db: aiosqlite.Connection = Depends(get_db)
):
    # Validate file formats
    if not pdf.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="PDF file must have .pdf extension")
    if not json_file.filename.endswith(".json"):
        raise HTTPException(status_code=400, detail="JSON file must have .json extension")

    doc_id = str(uuid.uuid4())
    pdf_filename = f"{doc_id}_{pdf.filename}"
    json_filename = f"{doc_id}_{json_file.filename}"

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
        sections, footnotes = parse_json_document(json_content)
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
            INSERT INTO documents (id, name, pdf_filename, json_filename, total_sections, total_pages, uploaded_at, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (doc_id, name, pdf_filename, json_filename, total_sections, total_pages, uploaded_at, "pending")
        )

        # Insert sections
        for sec in sections:
            await db.execute(
                """
                INSERT INTO sections (
                    id, document_id, chapter_code, chapter_heading, part_code, part_heading,
                    division_code, division_heading, section_code, section_heading,
                    start_page, end_page, html_content, plain_text, sort_order, review_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    sec["id"], doc_id, sec["chapter_code"], sec["chapter_heading"],
                    sec["part_code"], sec["part_heading"], sec["division_code"], sec["division_heading"],
                    sec["section_code"], sec["section_heading"], sec["start_page"], sec["end_page"],
                    sec["html_content"], sec["plain_text"], sec["sort_order"], sec["review_status"]
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
        stats=DocumentStats(reviewed=0, approved=0, has_issues=0, pending=total_sections)
    )

@router.get("", response_model=list[DocumentResponse])
async def list_documents(db: aiosqlite.Connection = Depends(get_db)):
    query = """
        SELECT 
            d.id, d.name, d.pdf_filename, d.json_filename, d.total_sections, d.total_pages, d.uploaded_at, d.status,
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
            d.id, d.name, d.pdf_filename, d.json_filename, d.total_sections, d.total_pages, d.uploaded_at, d.status,
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
