import os

import aiosqlite

DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
DB_PATH = os.path.join(DB_DIR, "qa_portal.db")

async def get_db():
    # Make sure DB directory exists
    os.makedirs(DB_DIR, exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA foreign_keys = ON;")
        await db.execute("PRAGMA cache_size = 500;")
        await db.execute("PRAGMA temp_store = FILE;")
        db.row_factory = aiosqlite.Row
        yield db

async def init_db():
    os.makedirs(DB_DIR, exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA foreign_keys = ON;")
        await db.execute("PRAGMA cache_size = 500;")
        await db.execute("PRAGMA temp_store = FILE;")
        
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
            status        TEXT NOT NULL DEFAULT 'pending',
            source_type   TEXT NOT NULL DEFAULT 'upload',
            source_key    TEXT,
            source_hash   TEXT
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
            review_status TEXT NOT NULL DEFAULT 'pending',
            source_key    TEXT
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
            html_content  TEXT,
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

        # Migration: Add html_content column to footnotes if it doesn't exist
        try:
            async with db.execute("SELECT html_content FROM footnotes LIMIT 1;") as _:
                pass
        except Exception:
            try:
                await db.execute("ALTER TABLE footnotes ADD COLUMN html_content TEXT;")
                await db.commit()
            except Exception as migrate_err:
                print(f"Migration error (html_content): {migrate_err}")

        # Corpus-source migrations for existing portal databases.
        for column, ddl in (
            (
                "source_type",
                "ALTER TABLE documents ADD COLUMN source_type TEXT NOT NULL DEFAULT 'upload';",
            ),
            ("source_key", "ALTER TABLE documents ADD COLUMN source_key TEXT;"),
            ("source_hash", "ALTER TABLE documents ADD COLUMN source_hash TEXT;"),
        ):
            try:
                async with db.execute(
                    f"SELECT {column} FROM documents LIMIT 1;"
                ) as _:
                    pass
            except Exception:
                try:
                    await db.execute(ddl)
                except Exception as migrate_err:
                    print(f"Migration error (documents.{column}): {migrate_err}")

        try:
            async with db.execute("SELECT source_key FROM sections LIMIT 1;") as _:
                pass
        except Exception:
            try:
                await db.execute("ALTER TABLE sections ADD COLUMN source_key TEXT;")
            except Exception as migrate_err:
                print(f"Migration error (sections.source_key): {migrate_err}")

        # Indexes
        await db.execute("CREATE INDEX IF NOT EXISTS idx_sections_document ON sections(document_id);")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_sections_pages ON sections(document_id, start_page, end_page);")
        await db.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_documents_source
            ON documents(source_type, source_key)
            WHERE source_key IS NOT NULL;
            """
        )
        await db.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_sections_source
            ON sections(document_id, source_key)
            WHERE source_key IS NOT NULL;
            """
        )
        await db.execute("CREATE INDEX IF NOT EXISTS idx_footnotes_section ON footnotes(section_id);")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_annotations_section ON annotations(section_id);")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_annotations_footnote ON annotations(footnote_id);")

        # The original external-content FTS table used a column named
        # ``section_id`` that does not exist on ``sections`` (the real column
        # is ``id``), so reads failed with ``no such column: T.section_id``.
        # Migrate it once to a self-contained index with explicit triggers.
        async with db.execute(
            """
            SELECT sql FROM sqlite_master
            WHERE type = 'table' AND name = 'sections_fts'
            """
        ) as cursor:
            fts_row = await cursor.fetchone()
        if fts_row and "content=sections" in (fts_row[0] or "").replace(" ", ""):
            await db.execute("DROP TRIGGER IF EXISTS sections_ai;")
            await db.execute("DROP TRIGGER IF EXISTS sections_ad;")
            await db.execute("DROP TRIGGER IF EXISTS sections_au;")
            await db.execute("DROP TABLE sections_fts;")

        await db.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS sections_fts USING fts5(
            section_id,
            section_code,
            section_heading,
            chapter_code,
            plain_text
        );
        """)

        await db.execute("""
        CREATE TRIGGER IF NOT EXISTS sections_ai AFTER INSERT ON sections BEGIN
            INSERT INTO sections_fts(rowid, section_id, section_code, section_heading, chapter_code, plain_text)
            VALUES (new.rowid, new.id, new.section_code, new.section_heading, new.chapter_code, new.plain_text);
        END;
        """)

        await db.execute("""
        CREATE TRIGGER IF NOT EXISTS sections_ad AFTER DELETE ON sections BEGIN
            DELETE FROM sections_fts WHERE rowid = old.rowid;
        END;
        """)

        await db.execute("""
        CREATE TRIGGER IF NOT EXISTS sections_au AFTER UPDATE ON sections BEGIN
            DELETE FROM sections_fts WHERE rowid = old.rowid;
            INSERT INTO sections_fts(rowid, section_id, section_code, section_heading, chapter_code, plain_text)
            VALUES (new.rowid, new.id, new.section_code, new.section_heading, new.chapter_code, new.plain_text);
        END;
        """)

        async with db.execute("SELECT COUNT(*) FROM sections_fts;") as cursor:
            fts_count = (await cursor.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM sections;") as cursor:
            section_count = (await cursor.fetchone())[0]
        if fts_count != section_count:
            await db.execute("DELETE FROM sections_fts;")
            await db.execute(
                """
                INSERT INTO sections_fts(
                    rowid, section_id, section_code, section_heading,
                    chapter_code, plain_text
                )
                SELECT
                    rowid, id, section_code, section_heading,
                    chapter_code, plain_text
                FROM sections
                """
            )

        await db.commit()
