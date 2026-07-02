import os
import shutil
import uuid
import json
import asyncio
from datetime import datetime
import aiosqlite

from backend.database import get_db, init_db, DB_PATH
from backend.services.pdf_service import get_pdf_page_count
from backend.services.json_parser import parse_json_document

FBR_PARSING_DIR = "/Users/muhammad.husnain/Downloads/code/AG/FBR-Parsing"
MANIFEST_PATH = os.path.join(FBR_PARSING_DIR, "output/manifest.json")
PDF_DIR = os.path.join(FBR_PARSING_DIR, "Income Tax Ordinance")
JSON_DIR = os.path.join(FBR_PARSING_DIR, "output/enriched")
UPLOAD_DIR = "backend/uploads"

async def deploy_and_seed():
    print("Initializing Database Schema...")
    await init_db()
    
    if not os.path.exists(MANIFEST_PATH):
        print(f"Error: manifest.json not found at {MANIFEST_PATH}")
        return

    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA foreign_keys = ON;")
        
        for entry in manifest:
            filename = entry.get("filename")
            output_json = entry.get("output")
            sections_count = entry.get("sections", 0)
            
            # Skip if error entry or if 0 sections (short pamphlets/amendments)
            if "error" in entry or sections_count == 0:
                print(f"Skipping pamphlet/error entry: {filename}")
                continue
                
            pdf_src = os.path.join(PDF_DIR, filename)
            json_src = os.path.join(JSON_DIR, output_json)
            
            if not os.path.exists(pdf_src) or not os.path.exists(json_src):
                print(f"Skipping (files missing): {filename}")
                continue
                
            doc_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, filename))
            doc_name = filename.replace(".pdf", "").strip()
            
            pdf_dest_filename = f"{doc_id}_{filename.replace(' ', '_')}"
            json_dest_filename = f"{doc_id}_{output_json}"
            
            pdf_dest = os.path.join(UPLOAD_DIR, pdf_dest_filename)
            json_dest = os.path.join(UPLOAD_DIR, json_dest_filename)
            
            print(f"\nProcessing: {doc_name}")
            print(f"  → Copying PDF to {pdf_dest}")
            shutil.copy(pdf_src, pdf_dest)
            print(f"  → Copying JSON to {json_dest}")
            shutil.copy(json_src, json_dest)
            
            total_pages = get_pdf_page_count(pdf_dest)
            
            with open(json_dest, "r", encoding="utf-8") as f:
                json_content = f.read()
            
            try:
                sections, footnotes = parse_json_document(json_content)
            except Exception as e:
                print(f"  ERROR parsing JSON for {filename}: {e}")
                continue
                
            total_sections = len(sections)
            uploaded_at = datetime.utcnow().isoformat() + "Z"
            
            # Delete existing document record (cascades to sections, footnotes, annotations)
            print(f"  → Clearing existing DB records for: {doc_name} (ID: {doc_id})")
            await db.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
            await db.commit()
            
            print("  → Inserting document record...")
            await db.execute(
                """
                INSERT INTO documents (id, name, pdf_filename, json_filename, total_sections, total_pages, uploaded_at, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (doc_id, doc_name, pdf_dest_filename, json_dest_filename, total_sections, total_pages, uploaded_at, "pending")
            )
            
            print(f"  → Inserting {total_sections} sections...")
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
            
            print(f"  → Inserting {len(footnotes)} footnotes...")
            chunk_size = 500
            for i in range(0, len(footnotes), chunk_size):
                chunk = footnotes[i:i + chunk_size]
                for fn in chunk:
                    await db.execute(
                        """
                        INSERT INTO footnotes (id, section_id, marker, page, text, html_content, review_status)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (fn["id"], fn["section_id"], fn["marker"], fn["page"], fn["text"], fn.get("html_content", ""), fn["review_status"])
                    )
                await db.commit()
            
            print(f"Successfully seeded: {doc_name}")
            print("-" * 50)
            
    print("\nDATABASE DEPLOY AND SEEDING COMPLETE!")

if __name__ == "__main__":
    asyncio.run(deploy_and_seed())
