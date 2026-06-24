import os
import shutil
import uuid
import asyncio
from datetime import datetime
import aiosqlite

from backend.database import get_db, init_db, DB_PATH
from backend.services.pdf_service import get_pdf_page_count
from backend.services.json_parser import parse_json_document

PDF_SOURCE = "Assets/Income Tax Ordinance, 2001 Amended upto 30-06-2018.pdf"
JSON_SOURCE = "Assets/ordinance-2018-enriched.json"
UPLOAD_DIR = "backend/uploads"

async def seed():
    print("Initializing Database...")
    await init_db()
    
    # Check if files exist
    if not os.path.exists(PDF_SOURCE) or not os.path.exists(JSON_SOURCE):
        print(f"Error: Seeding files not found. Ensure {PDF_SOURCE} and {JSON_SOURCE} are present.")
        return

    os.makedirs(UPLOAD_DIR, exist_ok=True)

    # Generate document ID and copy files
    doc_id = str(uuid.uuid4())
    pdf_filename = f"{doc_id}_Income_Tax_Ordinance_2018.pdf"
    json_filename = f"{doc_id}_ordinance-2018-enriched.json"

    pdf_dest = os.path.join(UPLOAD_DIR, pdf_filename)
    json_dest = os.path.join(UPLOAD_DIR, json_filename)

    print("Copying files to uploads directory...")
    shutil.copy(PDF_SOURCE, pdf_dest)
    shutil.copy(JSON_SOURCE, json_dest)

    # Parse and count
    print("Reading PDF page count...")
    total_pages = get_pdf_page_count(pdf_dest)
    
    print("Parsing and flattening enriched JSON...")
    with open(json_dest, "r", encoding="utf-8") as f:
        json_content = f.read()
    sections, footnotes = parse_json_document(json_content)

    total_sections = len(sections)
    uploaded_at = datetime.utcnow().isoformat() + "Z"

    print(f"Connecting to database at {DB_PATH}...")
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA foreign_keys = ON;")
        
        # Check if already seeded
        async with db.execute("SELECT COUNT(*) FROM documents WHERE name = 'Income Tax Ordinance, 2001 (Amended 2018)'") as cursor:
            count = await cursor.fetchone()
            if count[0] > 0:
                print("Database is already seeded with this document.")
                return

        print("Inserting document record...")
        await db.execute(
            """
            INSERT INTO documents (id, name, pdf_filename, json_filename, total_sections, total_pages, uploaded_at, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (doc_id, "Income Tax Ordinance, 2001 (Amended 2018)", pdf_filename, json_filename, total_sections, total_pages, uploaded_at, "pending")
        )

        print(f"Inserting {total_sections} sections...")
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

        print(f"Inserting {len(footnotes)} footnotes...")
        # To avoid sqlite parameter limits, we insert in chunks
        chunk_size = 500
        for i in range(0, len(footnotes), chunk_size):
            chunk = footnotes[i:i + chunk_size]
            for fn in chunk:
                await db.execute(
                    """
                    INSERT INTO footnotes (id, section_id, marker, page, text, review_status)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (fn["id"], fn["section_id"], fn["marker"], fn["page"], fn["text"], fn["review_status"])
                )
            await db.commit()

        print("Commiting final changes...")
        await db.commit()

    print("=" * 60)
    print("DATABASE SEEDING SUCCESSFUL!")
    print(f"Document Name: Income Tax Ordinance, 2001 (Amended 2018)")
    print(f"Sections Inserted: {total_sections}")
    print(f"Footnotes Inserted: {len(footnotes)}")
    print(f"PDF Pages: {total_pages}")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(seed())
