import os, sqlite3, logging, ssl
from pathlib import Path
from contextlib import contextmanager
from urllib.parse import urlparse
from dotenv import load_dotenv

# Load from backend/.env or root .env
_env_path = Path(__file__).resolve().parent.parent / ".env"
if _env_path.exists():
    load_dotenv(_env_path)
else:
    load_dotenv()

logger = logging.getLogger("actionpilot.db")

def get_database_url() -> str:
    return os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL") or ""

def is_postgres() -> bool:
    if os.getenv("PYTEST_CURRENT_TEST"):
        return False
    url = get_database_url().strip()
    return url.startswith("postgres://") or url.startswith("postgresql://")

def resolve_sqlite_path() -> str:
    custom = os.getenv("ACTIONPILOT_DB_PATH")
    if custom:
        p = Path(custom).resolve()
        p.parent.mkdir(parents=True, exist_ok=True)
        return str(p)

    if os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME") or os.getenv("LAMBDA_TASK_ROOT"):
        return "/tmp/actionpilot.db"

    default_dir = Path(__file__).resolve().parent.parent
    try:
        default_dir.mkdir(parents=True, exist_ok=True)
        test_file = default_dir / ".db_write_probe"
        test_file.touch()
        test_file.unlink(missing_ok=True)
        return str(default_dir / "actionpilot.db")
    except (OSError, PermissionError):
        logger.warning("Default directory %s is read-only. Falling back to /tmp/actionpilot.db", default_dir)
        return "/tmp/actionpilot.db"

DB_PATH = resolve_sqlite_path()

# -------------------------------------------------------------
# PostgreSQL Wrapper for SQLite DB-API compatibility
# -------------------------------------------------------------

class PgRow:
    """Dict-accessible and index-accessible row wrapper matching sqlite3.Row."""
    def __init__(self, cols, values):
        self._cols = {c: i for i, c in enumerate(cols)}
        self._values = list(values)

    def __getitem__(self, key):
        if isinstance(key, int):
            return self._values[key]
        return self._values[self._cols[key]]

    def __contains__(self, key):
        return key in self._cols

    def get(self, key, default=None):
        if key in self._cols:
            return self._values[self._cols[key]]
        return default

    def keys(self):
        return self._cols.keys()

    def values(self):
        return self._values

    def items(self):
        return zip(self._cols.keys(), self._values)

    def __iter__(self):
        return iter(self._cols.keys())

    def __len__(self):
        return len(self._values)

    def __repr__(self):
        return f"PgRow({dict(self.items())})"

class PgCursorWrapper:
    """
    Wraps a pg8000 cursor to:
    - Automatically convert SQLite '?' parameter placeholders to PostgreSQL '%s'
    - Return self from execute() so c.execute(...).fetchone() chains cleanly
    - Return PgRow objects matching sqlite3.Row behavior
    """
    def __init__(self, cursor):
        self.cursor = cursor
        self.description = None

    def execute(self, sql, params=None):
        pg_sql = sql.replace("?", "%s")
        if params is not None:
            self.cursor.execute(pg_sql, tuple(params))
        else:
            self.cursor.execute(pg_sql)
        self.description = self.cursor.description
        return self

    def executemany(self, sql, seq_of_params):
        pg_sql = sql.replace("?", "%s")
        for p in seq_of_params:
            self.cursor.execute(pg_sql, tuple(p))
        return self

    def executescript(self, script):
        for stmt in script.strip().split(";"):
            clean = stmt.strip()
            if clean:
                self.execute(clean)
        return self

    def fetchone(self):
        row = self.cursor.fetchone()
        if not row:
            return None
        cols = [d[0] for d in self.description]
        return PgRow(cols, row)

    def fetchall(self):
        rows = self.cursor.fetchall()
        if not rows:
            return []
        cols = [d[0] for d in self.description]
        return [PgRow(cols, r) for r in rows]

# -------------------------------------------------------------
# Database Connection Context Manager
# -------------------------------------------------------------

@contextmanager
def connect():
    """
    Unified database connection context manager:
    - If DATABASE_URL is set, connects to PostgreSQL (Neon.tech / Supabase / Render Postgres).
    - Otherwise, connects to local SQLite with WAL mode and foreign keys.
    """
    if is_postgres():
        import pg8000.dbapi
        p = urlparse(get_database_url())
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE

        conn = pg8000.dbapi.connect(
            user=p.username,
            password=p.password,
            host=p.hostname,
            port=p.port or 5432,
            database=p.path.lstrip("/"),
            ssl_context=ssl_ctx
        )
        cur = conn.cursor()
        wrapped = PgCursorWrapper(cur)
        try:
            yield wrapped
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    else:
        Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
        c = sqlite3.connect(DB_PATH, timeout=20)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA foreign_keys=ON")
        try:
            c.execute("PRAGMA journal_mode=WAL")
        except Exception:
            pass
        c.execute("PRAGMA busy_timeout=20000")
        try:
            yield c
            c.commit()
        except Exception:
            c.rollback()
            raise
        finally:
            c.close()

# -------------------------------------------------------------
# Diagnostic Health Check
# -------------------------------------------------------------

def check_db_health() -> dict:
    """Diagnostic check for database connectivity, active engine, and table counts."""
    try:
        with connect() as c:
            if is_postgres():
                p = urlparse(get_database_url())
                c.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
                tables = [r[0] for r in c.fetchall()]
                user_count = c.execute("SELECT count(*) FROM users").fetchone()[0] if "users" in tables else 0
                task_count = c.execute("SELECT count(*) FROM tasks").fetchone()[0] if "tasks" in tables else 0
                doc_count = c.execute("SELECT count(*) FROM documents").fetchone()[0] if "documents" in tables else 0
                return {
                    "ok": True,
                    "engine": "postgresql",
                    "host": p.hostname,
                    "database": p.path.lstrip("/"),
                    "tables": tables,
                    "counts": {
                        "users": user_count,
                        "tasks": task_count,
                        "documents": doc_count
                    }
                }
            else:
                tables = [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
                user_count = c.execute("SELECT count(*) FROM users").fetchone()[0] if "users" in tables else 0
                task_count = c.execute("SELECT count(*) FROM tasks").fetchone()[0] if "tasks" in tables else 0
                doc_count = c.execute("SELECT count(*) FROM documents").fetchone()[0] if "documents" in tables else 0
                return {
                    "ok": True,
                    "engine": "sqlite",
                    "db_path": DB_PATH,
                    "is_wal": True,
                    "tables": tables,
                    "counts": {
                        "users": user_count,
                        "tasks": task_count,
                        "documents": doc_count
                    }
                }
    except Exception as e:
        return {
            "ok": False,
            "engine": "postgresql" if is_postgres() else "sqlite",
            "error": str(e)
        }

# -------------------------------------------------------------
# Schema Initialization & Auto-Migration
# -------------------------------------------------------------

def init_db():
    with connect() as c:
        if is_postgres():
            # PostgreSQL Schema
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
                id SERIAL PRIMARY KEY,
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
                id SERIAL PRIMARY KEY,
                user_id TEXT REFERENCES users(id) ON DELETE CASCADE,
                entity_type TEXT NOT NULL,
                entity_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                actor TEXT NOT NULL,
                details TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
            CREATE INDEX IF NOT EXISTS idx_verification_email ON verification_codes(email);
            CREATE INDEX IF NOT EXISTS idx_verification_code ON verification_codes(code);
            CREATE INDEX IF NOT EXISTS idx_documents_user ON documents(user_id);
            CREATE INDEX IF NOT EXISTS idx_tasks_document ON tasks(document_id);
            CREATE INDEX IF NOT EXISTS idx_tasks_user ON tasks(user_id);
            CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_events(user_id);
            CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_events(created_at DESC);
            """)

            # Migration check: Ensure user_id column exists
            for table in ("documents", "tasks", "audit_events"):
                cols = [r[0] for r in c.execute("SELECT column_name FROM information_schema.columns WHERE table_name = ?", (table,)).fetchall()]
                if cols and "user_id" not in cols:
                    c.execute(f"ALTER TABLE {table} ADD COLUMN user_id TEXT REFERENCES users(id) ON DELETE CASCADE")

            task_cols = [r[0] for r in c.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'tasks'").fetchall()]
            if task_cols and "dispatched" not in task_cols:
                c.execute("ALTER TABLE tasks ADD COLUMN dispatched INTEGER NOT NULL DEFAULT 0")
            if task_cols and "dispatched_at" not in task_cols:
                c.execute("ALTER TABLE tasks ADD COLUMN dispatched_at TEXT")
            if task_cols and "dispatch_channel" not in task_cols:
                c.execute("ALTER TABLE tasks ADD COLUMN dispatch_channel TEXT")

        else:
            # SQLite Schema
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

            CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
            CREATE INDEX IF NOT EXISTS idx_verification_email ON verification_codes(email);
            CREATE INDEX IF NOT EXISTS idx_verification_code ON verification_codes(code);
            CREATE INDEX IF NOT EXISTS idx_documents_user ON documents(user_id);
            CREATE INDEX IF NOT EXISTS idx_tasks_document ON tasks(document_id);
            CREATE INDEX IF NOT EXISTS idx_tasks_user ON tasks(user_id);
            CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_events(user_id);
            CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_events(created_at DESC);
            """)

            for table in ("documents", "tasks", "audit_events"):
                cols = [row[1] for row in c.execute(f"PRAGMA table_info({table})").fetchall()]
                if "user_id" not in cols:
                    c.execute(f"ALTER TABLE {table} ADD COLUMN user_id TEXT REFERENCES users(id) ON DELETE CASCADE")

            task_cols = [row[1] for row in c.execute("PRAGMA table_info(tasks)").fetchall()]
            if "dispatched" not in task_cols:
                c.execute("ALTER TABLE tasks ADD COLUMN dispatched INTEGER NOT NULL DEFAULT 0")
            if "dispatched_at" not in task_cols:
                c.execute("ALTER TABLE tasks ADD COLUMN dispatched_at TEXT")
            if "dispatch_channel" not in task_cols:
                c.execute("ALTER TABLE tasks ADD COLUMN dispatch_channel TEXT")

        # Auto-seed default judge / demo account if users table is empty and not running under tests
        if not os.getenv("PYTEST_CURRENT_TEST"):
            has_user = c.execute("SELECT 1 FROM users LIMIT 1").fetchone()
            if not has_user:
                demo_uid = "usr_demo_judge_2026"
                demo_email = "judge@hackathon.com"
                demo_hash = "pbkdf2:sha256:100000:fd052e4409164df363712ecf694269db:c386ce1b0fd4bb0b99d7153714fc4df88163903b00ee9a45dd2a77107d01a285"  # password123
                demo_now = "2026-10-25T00:00:00+00:00"
                c.execute(
                    "INSERT INTO users(id, email, password_hash, full_name, is_verified, created_at) VALUES(?,?,?,?,1,?)",
                    (demo_uid, demo_email, demo_hash, "Hackathon Judge", demo_now)
                )
