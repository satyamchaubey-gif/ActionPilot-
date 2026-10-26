import hashlib, json, os, uuid, logging, re, urllib.parse
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional
import httpx
from fastapi import FastAPI, UploadFile, File, HTTPException, Query, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

from . import db
from .schemas import (
    TextIngest, TaskPatch, ActionDraft,
    UserSignUp, UserLogin, VerifyEmail, ResendCode,
    AuthResponse, UserResponse, UserProfileUpdate,
    MeetingCreate, MeetingResponse,
    DispatchAction, ConflictResolution, DemoPresetRequest
)
from .extractor import extract_tasks
from .auth import hash_password, verify_password, create_access_token, get_current_user
from .email_service import generate_otp, store_verification_code, verify_code, send_verification_email

load_dotenv()

app = FastAPI(
    title="ActionPilot API",
    version="0.2.0",
    description="Evidence-driven, human-approved workflow orchestration with user auth"
)

cors_origins_env = os.environ.get("CORS_ORIGINS")
allowed_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
]
if cors_origins_env:
    allowed_origins.extend([o.strip() for o in cors_origins_env.split(",") if o.strip()])

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?|https://.*\.vercel\.app|https://.*\.onrender\.com",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
ALLOWED_TASK_FIELDS = {"title", "description", "assignee", "due_date", "priority"}

def now():
    return datetime.now(timezone.utc).isoformat()

def uid():
    return str(uuid.uuid4())

def audit(c, typ, eid, event, details, actor="system", user_id=None):
    c.execute(
        "INSERT INTO audit_events(user_id,entity_type,entity_id,event_type,actor,details,created_at) VALUES(?,?,?,?,?,?,?)",
        (user_id, typ, eid, event, actor, json.dumps(details, ensure_ascii=False), now())
    )

def decode_row(r):
    if not r:
        return None
    d = dict(r)
    for k in ("dependencies", "evidence", "uncertainty_flags"):
        if k in d and isinstance(d[k], str):
            try:
                d[k] = json.loads(d[k])
            except Exception:
                pass
    return d

async def ingest(title: str, filename: Optional[str], content: str, user_id: str, actor: str):
    digest = hashlib.sha256(content.encode()).hexdigest()
    with db.connect() as c:
        old = c.execute("SELECT * FROM documents WHERE user_id=? AND content_hash=?", (user_id, digest)).fetchone()
        if old:
            # Check if this document has tasks currently in database
            existing_tasks = c.execute("SELECT count(*) FROM tasks WHERE document_id=? AND user_id=?", (old["id"], user_id)).fetchone()[0]
            if existing_tasks > 0:
                audit(c, "document", old["id"], "duplicate_ingestion_skipped", {"sha256": digest, "existing_tasks": existing_tasks}, actor=actor, user_id=user_id)
                return old["id"], True

    result = await extract_tasks(content, filename or title)
    did = uid()

    with db.connect() as c:
        old = c.execute("SELECT * FROM documents WHERE user_id=? AND content_hash=?", (user_id, digest)).fetchone()
        if old:
            existing_tasks = c.execute("SELECT count(*) FROM tasks WHERE document_id=? AND user_id=?", (old["id"], user_id)).fetchone()[0]
            if existing_tasks > 0:
                audit(c, "document", old["id"], "duplicate_ingestion_skipped", {"sha256": digest, "existing_tasks": existing_tasks}, actor=actor, user_id=user_id)
                return old["id"], True

        c.execute(
            "INSERT INTO documents(id,user_id,title,filename,content,content_hash,created_at,status) VALUES(?,?,?,?,?,?,?,?)",
            (did, user_id, title, filename, content, digest, now(), "processed")
        )
        audit(c, "document", did, "document_ingested", {"title": title, "filename": filename, "sha256": digest}, actor=actor, user_id=user_id)

        for t in result.tasks:
            tid = uid()
            c.execute(
                """INSERT INTO tasks(id,user_id,document_id,title,description,assignee,due_date,priority,dependencies,evidence,confidence,uncertainty_flags,status,created_at,updated_at)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    tid, user_id, did, t.title, t.description, t.assignee,
                    t.due_date.isoformat() if t.due_date else None,
                    t.priority, json.dumps(t.dependencies),
                    json.dumps([e.model_dump(mode="json") for e in t.evidence]),
                    t.confidence, json.dumps(t.uncertainty_flags),
                    "proposed", now(), now()
                )
            )
            audit(c, "task", tid, "task_proposed", {"document_id": did, "title": t.title, "confidence": t.confidence}, actor=actor, user_id=user_id)

        audit(c, "document", did, "extraction_completed", {"task_count": len(result.tasks), "notes": result.extraction_notes}, actor=actor, user_id=user_id)

    return did, False

@app.on_event("startup")
def startup():
    db.init_db()

@app.get("/api/health")
def health():
    db_status = db.check_db_health()
    return {
        "status": "ok" if db_status.get("ok") else "degraded",
        "service": "ActionPilot API",
        "database": db_status,
        "auth_enabled": True,
        "email_verification": bool(os.getenv("SMTP_USER") and os.getenv("SMTP_PASS")),
        "llm_mode": os.getenv("ACTIONPILOT_LLM_MODE", "local")
    }

# -------------------------------------------------------------
# Authentication Routes
# -------------------------------------------------------------

@app.post("/api/auth/signup", response_model=AuthResponse)
def signup(payload: UserSignUp):
    email = payload.email.lower().strip()
    if not EMAIL_REGEX.match(email):
        raise HTTPException(status_code=400, detail="Please enter a valid email address.")
    if len(payload.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters.")

    full_name = payload.full_name.strip()
    with db.connect() as c:
        existing = c.execute("SELECT id, email, is_verified FROM users WHERE email=?", (email,)).fetchone()
        if existing:
            if existing["is_verified"]:
                raise HTTPException(status_code=409, detail="An account with this email already exists. Please sign in.")
            user_id = existing["id"]
            # Update password and name for unverified re-signup
            c.execute(
                "UPDATE users SET password_hash=?, full_name=? WHERE id=?",
                (hash_password(payload.password), full_name, user_id)
            )
        else:
            user_id = uid()
            c.execute(
                "INSERT INTO users(id, email, password_hash, full_name, is_verified, created_at) VALUES(?,?,?,?,0,?)",
                (user_id, email, hash_password(payload.password), full_name, now())
            )

    code = generate_otp()
    store_verification_code(user_id, email, code)
    email_res = send_verification_email(email, code, full_name)

    return AuthResponse(
        requires_verification=True,
        message=f"Verification code sent to {email}. Check your inbox.",
        dev_code=email_res.get("dev_code")
    )

@app.post("/api/auth/verify-email", response_model=AuthResponse)
def verify_email(payload: VerifyEmail):
    email = payload.email.lower().strip()
    code = payload.code.strip()

    with db.connect() as c:
        user_row = c.execute("SELECT id, email, full_name, is_verified, created_at FROM users WHERE email=?", (email,)).fetchone()
        if not user_row:
            raise HTTPException(status_code=404, detail="Account not found. Please register first.")
        user = dict(user_row)

    if not verify_code(email, code):
        raise HTTPException(status_code=400, detail="Invalid or expired verification code. Please request a new one.")

    with db.connect() as c:
        c.execute("UPDATE users SET is_verified=1 WHERE id=?", (user["id"],))
        audit(c, "user", user["id"], "user_email_verified", {"email": email}, actor=email, user_id=user["id"])

    user["is_verified"] = True
    token = create_access_token(user["id"], user["email"])

    return AuthResponse(
        token=token,
        user=UserResponse(**user),
        requires_verification=False,
        message="Email successfully verified! Welcome to ActionPilot."
    )

@app.post("/api/auth/resend-code")
def resend_code(payload: ResendCode):
    email = payload.email.lower().strip()
    with db.connect() as c:
        user = c.execute("SELECT id, email, full_name, is_verified FROM users WHERE email=?", (email,)).fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="No account registered with this email.")
        if user["is_verified"]:
            raise HTTPException(status_code=400, detail="Your email is already verified. Please sign in.")

        user_id = user["id"]
        full_name = user["full_name"]

    code = generate_otp()
    store_verification_code(user_id, email, code)
    email_res = send_verification_email(email, code, full_name)

    return {
        "success": True,
        "message": f"A new verification code has been sent to {email}.",
        "dev_code": email_res.get("dev_code")
    }

@app.post("/api/auth/login", response_model=AuthResponse)
def login(payload: UserLogin):
    email = payload.email.lower().strip()
    with db.connect() as c:
        user_row = c.execute("SELECT id, email, password_hash, full_name, is_verified, created_at FROM users WHERE email=?", (email,)).fetchone()
        if not user_row or not verify_password(payload.password, user_row["password_hash"]):
            raise HTTPException(status_code=401, detail="Invalid email or password.")

        user = dict(user_row)
        user_id = user["id"]

        if not user["is_verified"]:
            # Resend verification code automatically
            code = generate_otp()
            store_verification_code(user_id, email, code)
            email_res = send_verification_email(email, code, user.get("full_name", ""))
            return AuthResponse(
                requires_verification=True,
                message=f"Please verify your email address to continue. A code was sent to {email}.",
                dev_code=email_res.get("dev_code")
            )

        audit(c, "user", user_id, "user_logged_in", {"email": email}, actor=email, user_id=user_id)

    prefs = user.get("preferences") or {}
    if isinstance(prefs, str):
        try: prefs = json.loads(prefs)
        except: prefs = {}

    user_resp = UserResponse(
        id=user["id"],
        email=user["email"],
        full_name=user["full_name"],
        contact_no=user.get("contact_no") or "",
        age=user.get("age"),
        job_title=user.get("job_title") or "",
        preferences=prefs,
        is_verified=bool(user["is_verified"]),
        created_at=user["created_at"]
    )
    token = create_access_token(user_id, email)
    return AuthResponse(
        token=token,
        user=user_resp,
        requires_verification=False,
        message="Signed in successfully"
    )

@app.get("/api/auth/me", response_model=UserResponse)
def get_me(current_user: dict = Depends(get_current_user)):
    prefs = current_user.get("preferences") or {}
    if isinstance(prefs, str):
        try: prefs = json.loads(prefs)
        except: prefs = {}
    return UserResponse(
        id=current_user["id"],
        email=current_user["email"],
        full_name=current_user["full_name"],
        contact_no=current_user.get("contact_no") or "",
        age=current_user.get("age"),
        job_title=current_user.get("job_title") or "",
        preferences=prefs,
        is_verified=bool(current_user["is_verified"]),
        created_at=current_user["created_at"]
    )

@app.patch("/api/auth/profile", response_model=AuthResponse)
def update_profile(
    payload: UserProfileUpdate,
    current_user: dict = Depends(get_current_user)
):
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(400, "No profile changes provided")

    user_id = current_user["id"]
    new_email = current_user["email"]

    with db.connect() as c:
        if "email" in updates and updates["email"]:
            clean_email = updates["email"].lower().strip()
            if not EMAIL_REGEX.match(clean_email):
                raise HTTPException(400, "Invalid email address format.")
            if clean_email != current_user["email"]:
                existing = c.execute("SELECT id FROM users WHERE email=? AND id != ?", (clean_email, user_id)).fetchone()
                if existing:
                    raise HTTPException(409, "Email is already in use by another account.")
                new_email = clean_email
                updates["email"] = clean_email

        set_clauses = []
        params = []
        for k, v in updates.items():
            if k in ("full_name", "email", "contact_no", "age", "job_title"):
                set_clauses.append(f"{k} = ?")
                params.append(v)
            elif k == "preferences" and isinstance(v, dict):
                set_clauses.append("preferences = ?")
                params.append(json.dumps(v))

        if set_clauses:
            params.append(user_id)
            c.execute(f"UPDATE users SET {', '.join(set_clauses)} WHERE id = ?", params)
            audit(c, "user", user_id, "user_profile_updated", updates, actor=new_email, user_id=user_id)

        updated_row = c.execute("SELECT id, email, full_name, contact_no, age, job_title, preferences, is_verified, created_at FROM users WHERE id=?", (user_id,)).fetchone()
        u = dict(updated_row)
        u_prefs = u.get("preferences") or {}
        if isinstance(u_prefs, str):
            try: u_prefs = json.loads(u_prefs)
            except: u_prefs = {}

    token = create_access_token(user_id, new_email)
    return AuthResponse(
        token=token,
        user=UserResponse(
            id=u["id"],
            email=u["email"],
            full_name=u["full_name"],
            contact_no=u.get("contact_no") or "",
            age=u.get("age"),
            job_title=u.get("job_title") or "",
            preferences=u_prefs,
            is_verified=bool(u["is_verified"]),
            created_at=u["created_at"]
        ),
        requires_verification=False,
        message="Profile and settings updated successfully!"
    )

# -------------------------------------------------------------
# Meetings & Voice Notes History
# -------------------------------------------------------------

@app.get("/api/meetings")
def list_meetings(
    limit: int = Query(50, ge=1, le=200),
    current_user: dict = Depends(get_current_user)
):
    with db.connect() as c:
        rows = c.execute(
            "SELECT * FROM meetings WHERE user_id = ? ORDER BY recorded_at DESC LIMIT ?",
            (current_user["id"], limit)
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            if isinstance(d.get("speakers"), str):
                try: d["speakers"] = json.loads(d["speakers"])
                except: d["speakers"] = []
            result.append(d)
        return result

@app.post("/api/meetings")
async def save_meeting(
    payload: MeetingCreate,
    current_user: dict = Depends(get_current_user)
):
    mid = uid()
    rec_time = now()
    speakers_list = payload.speakers or ["Speaker 1"]
    speakers_json = json.dumps(speakers_list)
    task_count = 0

    if payload.auto_extract_tasks:
        try:
            did, dup = await ingest(
                payload.title,
                f"meeting_{mid[:8]}.txt",
                payload.transcript,
                user_id=current_user["id"],
                actor=current_user["email"]
            )
            with db.connect() as c:
                task_count = c.execute("SELECT count(*) FROM tasks WHERE document_id = ? AND user_id = ?", (did, current_user["id"])).fetchone()[0]
        except Exception as e:
            logging.getLogger("actionpilot").warning("Auto extraction on meeting failed: %s", e)

    with db.connect() as c:
        c.execute(
            """INSERT INTO meetings(id, user_id, title, recorded_at, duration_seconds, transcript, speakers, task_count, created_at)
               VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (mid, current_user["id"], payload.title, rec_time, payload.duration_seconds, payload.transcript, speakers_json, task_count, rec_time)
        )
        audit(c, "meeting", mid, "meeting_recorded", {"title": payload.title, "duration": payload.duration_seconds, "task_count": task_count}, actor=current_user["email"], user_id=current_user["id"])

    return {
        "id": mid,
        "title": payload.title,
        "recorded_at": rec_time,
        "duration_seconds": payload.duration_seconds,
        "transcript": payload.transcript,
        "speakers": speakers_list,
        "task_count": task_count,
        "created_at": rec_time,
        "message": "Meeting note recorded and saved to History!"
    }

@app.delete("/api/meetings/{mid}")
def delete_meeting(
    mid: str,
    current_user: dict = Depends(get_current_user)
):
    with db.connect() as c:
        existing = c.execute("SELECT id FROM meetings WHERE id=? AND user_id=?", (mid, current_user["id"])).fetchone()
        if not existing:
            raise HTTPException(404, "Meeting record not found")
        c.execute("DELETE FROM meetings WHERE id=? AND user_id=?", (mid, current_user["id"]))
        audit(c, "meeting", mid, "meeting_deleted", {}, actor=current_user["email"], user_id=current_user["id"])
    return {"success": True, "message": "Meeting note deleted from history."}

# -------------------------------------------------------------
# Documents & Workflows (Scoped to Authenticated User)
# -------------------------------------------------------------

@app.post("/api/documents")
async def upload_document(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    name = file.filename or "upload.txt"
    suffix = Path(name).suffix.lower()
    if suffix in (".mp3", ".wav", ".m4a", ".webm", ".ogg"):
        raise HTTPException(400, "For audio notes, please use the Voice Studio recorder or paste the transcript into notes.")
    if suffix not in (".txt", ".md", ".csv", ".pdf", ".json", ".log"):
        raise HTTPException(415, "Supported formats: TXT, Markdown, CSV, PDF, JSON, LOG")
    raw = await file.read()
    if len(raw) > 10 * 1024 * 1024:
        raise HTTPException(413, "Maximum upload size is 10 MB")
    if suffix == ".pdf":
        try:
            from pypdf import PdfReader
            import io
            content = "\n".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(raw)).pages)
        except Exception as e:
            raise HTTPException(400, f"Could not parse PDF: {e}")
    else:
        content = raw.decode("utf-8", errors="replace")
    if not content.strip():
        raise HTTPException(400, "No readable text found")

    did, dup = await ingest(
        Path(name).stem,
        name,
        content,
        user_id=current_user["id"],
        actor=current_user["email"]
    )
    return {"document_id": did, "duplicate": dup, "message": "Duplicate skipped" if dup else "Processed"}

@app.post("/api/documents/text")
async def ingest_text(
    payload: TextIngest,
    current_user: dict = Depends(get_current_user)
):
    did, dup = await ingest(
        payload.title,
        None,
        payload.text,
        user_id=current_user["id"],
        actor=current_user["email"]
    )
    return {"document_id": did, "duplicate": dup, "message": "Duplicate skipped" if dup else "Processed"}

@app.get("/api/documents")
def documents(current_user: dict = Depends(get_current_user)):
    with db.connect() as c:
        return [
            dict(r) for r in c.execute(
                """SELECT d.id, d.title, d.filename, d.created_at, d.status,
                          (SELECT COUNT(*) FROM tasks t WHERE t.document_id = d.id AND t.user_id = d.user_id) task_count
                   FROM documents d
                   WHERE d.user_id = ?
                   ORDER BY d.created_at DESC""",
                (current_user["id"],)
            ).fetchall()
        ]

@app.get("/api/documents/{did}")
def document(did: str, current_user: dict = Depends(get_current_user)):
    with db.connect() as c:
        r = c.execute("SELECT * FROM documents WHERE id=? AND user_id=?", (did, current_user["id"])).fetchone()
        if not r:
            raise HTTPException(404, "Document not found")
        return dict(r)

@app.get("/api/tasks")
def tasks(
    document_id: Optional[str] = None,
    status: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    with db.connect() as c:
        q = "SELECT * FROM tasks WHERE user_id = ?"
        args = [current_user["id"]]
        if document_id:
            q += " AND document_id = ?"
            args.append(document_id)
        if status:
            q += " AND status = ?"
            args.append(status)
        q += " ORDER BY created_at DESC"
        return [decode_row(r) for r in c.execute(q, args).fetchall()]

@app.patch("/api/tasks/{tid}")
def edit_task(
    tid: str,
    payload: TaskPatch,
    current_user: dict = Depends(get_current_user)
):
    raw_changes = payload.model_dump(exclude_unset=True)
    if not raw_changes:
        raise HTTPException(400, "No fields supplied")
    if "title" in raw_changes and (not raw_changes["title"] or len(raw_changes["title"].strip()) < 3):
        raise HTTPException(422, "Title must be at least 3 characters")

    # Strictly whitelist allowed fields to prevent any dynamic injection
    changes = {k: v for k, v in raw_changes.items() if k in ALLOWED_TASK_FIELDS}
    if not changes:
        raise HTTPException(400, "No editable fields supplied")

    with db.connect() as c:
        old = c.execute("SELECT * FROM tasks WHERE id=? AND user_id=?", (tid, current_user["id"])).fetchone()
        if not old:
            raise HTTPException(404, "Task not found")
        if old["status"] not in ("proposed", "rejected", "approved"):
            raise HTTPException(409, f"Cannot edit task in state {old['status']}")

        before = {k: old[k] for k in changes}
        set_clauses = []
        params = []
        for k, v in changes.items():
            if hasattr(v, "isoformat") and v is not None:
                v = v.isoformat()
            if k == "assignee" and v == "":
                v = None
            set_clauses.append(f"{k} = ?")
            params.append(v)

        set_clauses.append("updated_at = ?")
        params.append(now())
        params.extend([tid, current_user["id"]])

        c.execute(f"UPDATE tasks SET {', '.join(set_clauses)} WHERE id = ? AND user_id = ?", params)
        audit(c, "task", tid, "task_edited", {"before": before, "after": changes}, actor=current_user["email"], user_id=current_user["id"])
        return decode_row(c.execute("SELECT * FROM tasks WHERE id=? AND user_id=?", (tid, current_user["id"])).fetchone())

@app.post("/api/tasks/{tid}/approve")
def approve(tid: str, current_user: dict = Depends(get_current_user)):
    with db.connect() as c:
        t = c.execute("SELECT * FROM tasks WHERE id=? AND user_id=?", (tid, current_user["id"])).fetchone()
        if not t:
            raise HTTPException(404, "Task not found")
        if t["status"] == "approved":
            return {"task_id": tid, "status": "approved", "idempotent": True}
        if t["status"] not in ("proposed", "rejected"):
            raise HTTPException(409, f"Cannot approve task in state {t['status']}")
        flags = json.loads(t["uncertainty_flags"])
        c.execute("UPDATE tasks SET status='approved', updated_at=? WHERE id=? AND user_id=?", (now(), tid, current_user["id"]))
        audit(c, "task", tid, "task_approved", {"title": t["title"], "warnings_present": bool(flags)}, actor=current_user["email"], user_id=current_user["id"])
        return {"task_id": tid, "status": "approved", "warnings_present": bool(flags)}

@app.post("/api/tasks/{tid}/reject")
def reject(tid: str, current_user: dict = Depends(get_current_user)):
    with db.connect() as c:
        t = c.execute("SELECT * FROM tasks WHERE id=? AND user_id=?", (tid, current_user["id"])).fetchone()
        if not t:
            raise HTTPException(404, "Task not found")
        if t["status"] not in ("proposed", "approved"):
            raise HTTPException(409, f"Cannot reject task in state {t['status']}")
        c.execute("UPDATE tasks SET status='rejected', updated_at=? WHERE id=? AND user_id=?", (now(), tid, current_user["id"]))
        audit(c, "task", tid, "task_rejected", {"title": t["title"]}, actor=current_user["email"], user_id=current_user["id"])
        return {"task_id": tid, "status": "rejected"}

@app.post("/api/tasks/{tid}/draft")
def create_draft(
    tid: str,
    payload: ActionDraft,
    current_user: dict = Depends(get_current_user)
):
    with db.connect() as c:
        t = c.execute("SELECT * FROM tasks WHERE id=? AND user_id=?", (tid, current_user["id"])).fetchone()
        if not t:
            raise HTTPException(404, "Task not found")
        if t["status"] != "approved":
            raise HTTPException(409, "Approve task before drafting")
        draft = {
            "channel": payload.channel,
            "recipient": payload.recipient,
            "subject": payload.subject,
            "body": payload.body,
            "created_at": now(),
            "sent": False
        }
        c.execute("UPDATE tasks SET draft=?, updated_at=? WHERE id=? AND user_id=?", (json.dumps(draft), now(), tid, current_user["id"]))
        audit(c, "task", tid, "action_draft_created", {"channel": payload.channel, "sent": False}, actor=current_user["email"], user_id=current_user["id"])
        return {"task_id": tid, "draft": draft, "message": "Draft saved. Nothing was sent."}

@app.post("/api/tasks/{tid}/dispatch")
async def dispatch_task(
    tid: str,
    payload: DispatchAction,
    current_user: dict = Depends(get_current_user)
):
    with db.connect() as c:
        t = c.execute("SELECT * FROM tasks WHERE id=? AND user_id=?", (tid, current_user["id"])).fetchone()
        if not t:
            raise HTTPException(404, "Task not found")
        if t["status"] != "approved":
            raise HTTPException(409, "Only approved tasks can be dispatched")

        task = decode_row(t)
        channel = payload.channel
        evidence_quote = task["evidence"][0]["quote"] if task.get("evidence") else ""
        
        dispatch_result = {
            "channel": channel,
            "simulated": payload.simulate,
            "dispatched_at": now(),
            "target": payload.target or "default",
        }

        # 1. Google Calendar Integration
        if channel == "calendar":
            due_str = task.get("due_date") or datetime.now(timezone.utc).strftime("%Y-%m-%d")
            try:
                d_obj = datetime.strptime(due_str, "%Y-%m-%d").date()
                end_obj = d_obj + timedelta(days=1)
                cal_start = d_obj.strftime("%Y%m%d")
                cal_end = end_obj.strftime("%Y%m%d")
            except Exception:
                cal_start = due_str.replace("-", "")
                cal_end = cal_start
            title_encoded = urllib.parse.quote(f"ActionPilot: {task['title']}")
            details = f"{task['description']}\n\nVerified Evidence: {evidence_quote}\nAudit ID: {tid}"
            details_encoded = urllib.parse.quote(details)
            cal_url = f"https://calendar.google.com/calendar/render?action=TEMPLATE&text={title_encoded}&dates={cal_start}/{cal_end}&details={details_encoded}"
            dispatch_result["calendar_url"] = cal_url
            dispatch_result["message"] = "Google Calendar event URL generated successfully!"

        # 2. Slack / Discord Webhook Integration
        elif channel in ("slack", "discord"):
            webhook_payload = {
                "text": f"🚀 *ActionPilot Verified Action* | `{task['priority'].upper()}`\n*Task:* {task['title']}\n*Assignee:* {task.get('assignee') or 'Unassigned'}\n*Due Date:* {task.get('due_date') or 'None'}\n> *Evidence Excerpt:* \"{evidence_quote}\"\n*Approved by:* {current_user['email']}",
                "channel": channel,
                "task_id": tid
            }
            if not payload.simulate and payload.target and payload.target.startswith("http"):
                try:
                    async with httpx.AsyncClient(timeout=10) as client:
                        r = await client.post(payload.target, json=webhook_payload)
                        r.raise_for_status()
                    dispatch_result["message"] = f"Live payload successfully sent to {channel} webhook!"
                except Exception as e:
                    dispatch_result["error"] = str(e)
                    dispatch_result["message"] = f"Webhook failed ({e}); recorded as simulated dispatch."
            else:
                dispatch_result["message"] = f"Action dispatched to {channel.capitalize()} (Simulated webhook delivery)"
            dispatch_result["payload"] = webhook_payload

        # 3. GitHub Issue Integration
        elif channel == "github":
            issue_title = urllib.parse.quote(task["title"])
            issue_body = urllib.parse.quote(f"### ActionPilot Task Proposal\n\n**Description:** {task['description']}\n**Priority:** {task['priority']}\n**Due Date:** {task.get('due_date')}\n\n> **Verified Evidence:**\n> {evidence_quote}\n\n*Approved in ActionPilot by:* {current_user['email']}")
            repo_target = payload.target.strip() if payload.target else "your-org/actionpilot-demo"
            repo_target = repo_target.replace("https://github.com/", "").strip("/")
            github_url = f"https://github.com/{repo_target}/issues/new?title={issue_title}&body={issue_body}"
            dispatch_result["github_url"] = github_url
            dispatch_result["message"] = "GitHub issue pre-fill link generated successfully!"

        # 4. Email Integration
        elif channel == "email":
            recip = payload.recipient or task.get("assignee") or current_user["email"]
            dispatch_result["recipient"] = recip
            dispatch_result["message"] = f"Action notification dispatched to {recip}"

        # Update database
        c.execute(
            "UPDATE tasks SET dispatched=1, dispatched_at=?, dispatch_channel=?, updated_at=? WHERE id=? AND user_id=?",
            (now(), channel, now(), tid, current_user["id"])
        )
        audit(
            c, "task", tid, "action_dispatched",
            {"channel": channel, "simulate": payload.simulate, "details": dispatch_result},
            actor=current_user["email"], user_id=current_user["id"]
        )

        return {
            "task_id": tid,
            "status": "dispatched",
            "dispatch": dispatch_result,
            "message": dispatch_result.get("message", "Task action successfully dispatched!")
        }

@app.post("/api/tasks/{tid}/resolve-conflict")
def resolve_conflict(
    tid: str,
    payload: ConflictResolution,
    current_user: dict = Depends(get_current_user)
):
    with db.connect() as c:
        t = c.execute("SELECT * FROM tasks WHERE id=? AND user_id=?", (tid, current_user["id"])).fetchone()
        if not t:
            raise HTTPException(404, "Task not found")

        old_flags = json.loads(t["uncertainty_flags"])
        # Remove conflict flags
        new_flags = [f for f in old_flags if "conflict" not in f.lower()]
        before_date = t["due_date"]
        resolved_date = payload.resolved_due_date.strip()

        c.execute(
            "UPDATE tasks SET due_date=?, uncertainty_flags=?, updated_at=? WHERE id=? AND user_id=?",
            (resolved_date, json.dumps(new_flags), now(), tid, current_user["id"])
        )
        audit(
            c, "task", tid, "conflict_resolved",
            {
                "before_date": before_date,
                "resolved_date": resolved_date,
                "rationale": payload.rationale,
                "remaining_flags": new_flags
            },
            actor=current_user["email"], user_id=current_user["id"]
        )
        return decode_row(c.execute("SELECT * FROM tasks WHERE id=? AND user_id=?", (tid, current_user["id"])).fetchone())

@app.post("/api/demo/preset")
async def load_demo_preset(
    payload: DemoPresetRequest,
    current_user: dict = Depends(get_current_user)
):
    presets = {
        "product_launch": {
            "title": "Product Launch Sync — 2026 Q4",
            "filename": "product_launch_sync.txt",
            "content": (
                "Product launch sync — meeting notes\n\n"
                "Action: Priya must send the launch plan by 2026-11-02. This is high priority.\n"
                "Action: Priya must send the launch plan by 2026-11-06. Updated note from the client says the plan is due on the later date.\n"
                "Please review the onboarding checklist by 2026-11-05.\n"
                "Owner: Daniel — publish the support FAQ by 2026-11-08.\n"
                "The team discussed the design refresh and agreed to revisit the topic next week."
            )
        },
        "security_incident": {
            "title": "Security Incident Brief — Sev 1 DB Access",
            "filename": "security_incident_response.txt",
            "content": (
                "Incident Response Call — Severity 1 Alert\n\n"
                "URGENT Action: DevSecOps team must rotate the compromised API credentials by 2026-10-24. Blocker for deployment.\n"
                "URGENT Action: DevSecOps team must rotate the compromised API credentials by 2026-10-23. Security lead confirmed rotation deadline was moved up.\n"
                "Action: Please audit VPC egress traffic logs by 2026-10-25.\n"
                "Owner: Rahul — notify external SOC audit partners by 2026-10-26.\n"
                "Security team recommends enforcing MFA across all tenant accounts."
            )
        },
        "exec_offsite": {
            "title": "Executive Offsite & Budget Alignment",
            "filename": "q4_strategy_offsite.txt",
            "content": (
                "Q4 Executive Strategy Offsite — Leadership Notes\n\n"
                "Action: Finance director must submit the finalized FY27 budget model by 2026-11-12. Critical priority.\n"
                "Action: Finance director must submit the finalized FY27 budget model by 2026-11-18. Revised after board subcommittee review.\n"
                "Action: Review vendor RFP proposals for AI infrastructure by 2026-11-15.\n"
                "Owner: Sarah — confirm keynote speaker travel itinerary by 2026-11-20.\n"
                "Team agreed on prioritizing customer retention over aggressive expansion."
            )
        }
    }
    preset_data = presets.get(payload.preset_id, presets["product_launch"])
    run_tag = f"\n\n[Scenario loaded at {now()}]"
    did, dup = await ingest(
        preset_data["title"],
        preset_data["filename"],
        preset_data["content"] + run_tag,
        user_id=current_user["id"],
        actor=current_user["email"]
    )
    return {
        "document_id": did,
        "preset_id": payload.preset_id,
        "title": preset_data["title"],
        "message": f"Demo scenario '{preset_data['title']}' loaded with conflict and evidence links!"
    }

@app.get("/api/audit")
def audit_log(
    limit: int = Query(100, ge=1, le=500),
    entity_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    with db.connect() as c:
        q = "SELECT * FROM audit_events WHERE user_id = ?"
        args = [current_user["id"]]
        if entity_id:
            q += " AND entity_id = ?"
            args.append(entity_id)
        q += " ORDER BY created_at DESC LIMIT ?"
        args.append(limit)
        return [{**dict(r), "details": json.loads(r["details"])} for r in c.execute(q, args).fetchall()]

@app.exception_handler(Exception)
async def unexpected_error(request, exc):
    logging.getLogger("actionpilot").exception("Unhandled API exception: %s", exc)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
