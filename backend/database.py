import os
import aiosqlite

DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
DB_PATH = os.path.join(DB_DIR, "qa_portal.db")

async def get_db():
    # Make sure DB directory exists
    os.makedirs(DB_DIR, exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        yield db

async def init_db():
    os.makedirs(DB_DIR, exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA foreign_keys = ON;")
        
        # Create documents table
        await db.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id            TEXT PRIMARY KEY,
            name          TEXT NOT NULL,
            pdf_filename  TEXT NOT NULL,
            json_filename TEXT NOT NULL,
            total_sections INTEGER NOT NULL,
            total_pages   INTEGER NOT NULL,
            uploaded_at   TEXT NOT NULL,
            status        TEXT NOT NULL DEFAULT 'pending'
        );
        """)

        # Create sections table
        await db.execute("""
        CREATE TABLE IF NOT EXISTS sections (
            id            TEXT PRIMARY KEY,
            document_id   TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
            chapter_code  TEXT,
            chapter_heading TEXT,
            part_code     TEXT,
            part_heading  TEXT,
            division_code TEXT,
            division_heading TEXT,
            section_code  TEXT NOT NULL,
            section_heading TEXT NOT NULL,
            start_page    INTEGER,
            end_page      INTEGER,
            html_content  TEXT,
            plain_text    TEXT,
            sort_order    INTEGER NOT NULL,
            review_status TEXT NOT NULL DEFAULT 'pending'
        );
        """)

        # Create footnotes table
        await db.execute("""
        CREATE TABLE IF NOT EXISTS footnotes (
            id            TEXT PRIMARY KEY,
            section_id    TEXT NOT NULL REFERENCES sections(id) ON DELETE CASCADE,
            marker        TEXT NOT NULL,
            page          INTEGER,
            text          TEXT NOT NULL,
            review_status TEXT NOT NULL DEFAULT 'pending'
        );
        """)

        # Create annotations table
        await db.execute("""
        CREATE TABLE IF NOT EXISTS annotations (
            id            TEXT PRIMARY KEY,
            section_id    TEXT NOT NULL REFERENCES sections(id) ON DELETE CASCADE,
            footnote_id   TEXT REFERENCES footnotes(id) ON DELETE CASCADE,
            highlighted_text TEXT NOT NULL,
            start_offset  INTEGER NOT NULL,
            end_offset    INTEGER NOT NULL,
            issue_description TEXT,
            severity      TEXT NOT NULL DEFAULT 'error',
            created_at    TEXT NOT NULL,
            reviewer_name TEXT,
            status        TEXT NOT NULL DEFAULT 'open'
        );
        """)

        # Migration: Add footnote_id column to existing databases if it doesn't exist
        try:
            async with db.execute("SELECT footnote_id FROM annotations LIMIT 1;") as _:
                pass
        except Exception:
            try:
                await db.execute("ALTER TABLE annotations ADD COLUMN footnote_id TEXT REFERENCES footnotes(id) ON DELETE CASCADE;")
                await db.commit()
            except Exception as migrate_err:
                print(f"Migration error (footnote_id): {migrate_err}")

        # Migration: Add status column to existing databases if it doesn't exist
        try:
            async with db.execute("SELECT status FROM annotations LIMIT 1;") as _:
                pass
        except Exception:
            try:
                await db.execute("ALTER TABLE annotations ADD COLUMN status TEXT NOT NULL DEFAULT 'open';")
                await db.commit()
            except Exception as migrate_err:
                print(f"Migration error (status): {migrate_err}")

        # Indexes
        await db.execute("CREATE INDEX IF NOT EXISTS idx_sections_document ON sections(document_id);")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_sections_pages ON sections(document_id, start_page, end_page);")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_footnotes_section ON footnotes(section_id);")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_annotations_section ON annotations(section_id);")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_annotations_footnote ON annotations(footnote_id);")

        # FTS5 Virtual Table
        await db.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS sections_fts USING fts5(
            section_id,
            section_code,
            section_heading,
            chapter_code,
            plain_text,
            content=sections,
            content_rowid=rowid
        );
        """)

        # FTS5 Triggers
        await db.execute("""
        CREATE TRIGGER IF NOT EXISTS sections_ai AFTER INSERT ON sections BEGIN
            INSERT INTO sections_fts(rowid, section_id, section_code, section_heading, chapter_code, plain_text)
            VALUES (new.rowid, new.id, new.section_code, new.section_heading, new.chapter_code, new.plain_text);
        END;
        """)

        await db.execute("""
        CREATE TRIGGER IF NOT EXISTS sections_ad AFTER DELETE ON sections BEGIN
            INSERT INTO sections_fts(sections_fts, rowid, section_id, section_code, section_heading, chapter_code, plain_text)
            VALUES('delete', old.rowid, old.id, old.section_code, old.section_heading, old.chapter_code, old.plain_text);
        END;
        """)

        await db.execute("""
        CREATE TRIGGER IF NOT EXISTS sections_au AFTER UPDATE ON sections BEGIN
            INSERT INTO sections_fts(sections_fts, rowid, section_id, section_code, section_heading, chapter_code, plain_text)
            VALUES('delete', old.rowid, old.id, old.section_code, old.section_heading, old.chapter_code, old.plain_text);
            INSERT INTO sections_fts(rowid, section_id, section_code, section_heading, chapter_code, plain_text)
            VALUES (new.rowid, new.id, new.section_code, new.section_heading, new.chapter_code, new.plain_text);
        END;
        """)

        await db.commit()
