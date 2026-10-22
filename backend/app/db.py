import os, sqlite3
from pathlib import Path

DB_PATH = os.getenv("ACTIONPILOT_DB_PATH", str(Path(__file__).resolve().parent.parent / "actionpilot.db"))

def connect():
    c = sqlite3.connect(DB_PATH, timeout=15)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    return c

def init_db():
    with connect() as c:
        # Create core tables
        c.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL DEFAULT '',
            is_verified INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS verification_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            email TEXT NOT NULL,
            code TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            used INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY,
            user_id TEXT REFERENCES users(id) ON DELETE CASCADE,
            title TEXT NOT NULL,
            filename TEXT,
            content TEXT NOT NULL,
            content_hash TEXT NOT NULL,
            created_at TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'processed'
        );

        CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY,
            user_id TEXT REFERENCES users(id) ON DELETE CASCADE,
            document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
            title TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            assignee TEXT,
            due_date TEXT,
            priority TEXT NOT NULL DEFAULT 'medium',
            dependencies TEXT NOT NULL DEFAULT '[]',
            evidence TEXT NOT NULL DEFAULT '[]',
            confidence REAL NOT NULL DEFAULT 0.65,
            uncertainty_flags TEXT NOT NULL DEFAULT '[]',
            status TEXT NOT NULL DEFAULT 'proposed',
            draft TEXT,
            dispatched INTEGER NOT NULL DEFAULT 0,
            dispatched_at TEXT,
            dispatch_channel TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS audit_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT REFERENCES users(id) ON DELETE CASCADE,
            entity_type TEXT NOT NULL,
            entity_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            actor TEXT NOT NULL,
            details TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        """)

        # Migration check: Ensure user_id column exists on pre-existing tables
        for table in ("documents", "tasks", "audit_events"):
            cols = [row[1] for row in c.execute(f"PRAGMA table_info({table})").fetchall()]
            if "user_id" not in cols:
                c.execute(f"ALTER TABLE {table} ADD COLUMN user_id TEXT REFERENCES users(id) ON DELETE CASCADE")

        # Migration check for new task dispatch columns
        task_cols = [row[1] for row in c.execute("PRAGMA table_info(tasks)").fetchall()]
        if "dispatched" not in task_cols:
            c.execute("ALTER TABLE tasks ADD COLUMN dispatched INTEGER NOT NULL DEFAULT 0")
        if "dispatched_at" not in task_cols:
            c.execute("ALTER TABLE tasks ADD COLUMN dispatched_at TEXT")
        if "dispatch_channel" not in task_cols:
            c.execute("ALTER TABLE tasks ADD COLUMN dispatch_channel TEXT")

        # Create indexes
        c.executescript("""
        CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
        CREATE INDEX IF NOT EXISTS idx_verification_email ON verification_codes(email);
        CREATE INDEX IF NOT EXISTS idx_verification_code ON verification_codes(code);
        CREATE INDEX IF NOT EXISTS idx_documents_user ON documents(user_id);
        CREATE INDEX IF NOT EXISTS idx_tasks_document ON tasks(document_id);
        CREATE INDEX IF NOT EXISTS idx_tasks_user ON tasks(user_id);
        CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_events(user_id);
        CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_events(created_at DESC);
        """)
