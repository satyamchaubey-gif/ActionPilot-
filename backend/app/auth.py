import os, hmac, hashlib, secrets, json, time, base64
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from . import db

SECRET_KEY = os.getenv("ACTIONPILOT_SECRET_KEY", "actionpilot_super_secret_development_key_change_in_production_2026")
TOKEN_EXPIRY_SECONDS = 7 * 24 * 3600  # 7 days

security_bearer = HTTPBearer(auto_error=False)

def hash_password(password: str) -> str:
    """Hash password using PBKDF2-HMAC-SHA256 with 100,000 iterations and 16 bytes salt."""
    salt = secrets.token_bytes(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    return f"pbkdf2:sha256:100000:{salt.hex()}:{key.hex()}"

def verify_password(password: str, hashed: str) -> bool:
    """Verify password against hashed string using constant-time comparison."""
    try:
        algo, hname, iters, salt_hex, key_hex = hashed.split(":")
        if algo != "pbkdf2" or hname != "sha256":
            return False
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(key_hex)
        computed = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, int(iters))
        return hmac.compare_digest(computed, expected)
    except Exception:
        return False

def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")

def _b64decode(data: str) -> bytes:
    pad = 4 - (len(data) % 4)
    if pad and pad != 4:
        data += "=" * pad
    return base64.urlsafe_b64decode(data.encode("utf-8"))

def create_access_token(user_id: str, email: str, expires_in: int = TOKEN_EXPIRY_SECONDS) -> str:
    """Create a signed HMAC-SHA256 JWT-compatible token."""
    header = {"alg": "HS256", "typ": "JWT"}
    now_ts = int(time.time())
    payload = {
        "sub": user_id,
        "email": email.lower().strip(),
        "iat": now_ts,
        "exp": now_ts + expires_in,
    }
    header_b64 = _b64encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = _b64encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    msg = f"{header_b64}.{payload_b64}".encode("utf-8")
    sig = hmac.new(SECRET_KEY.encode("utf-8"), msg, hashlib.sha256).digest()
    sig_b64 = _b64encode(sig)
    return f"{header_b64}.{payload_b64}.{sig_b64}"

def decode_access_token(token: str) -> Optional[dict]:
    """Validate signature and expiration of an access token."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        header_b64, payload_b64, sig_b64 = parts
        msg = f"{header_b64}.{payload_b64}".encode("utf-8")
        expected_sig = hmac.new(SECRET_KEY.encode("utf-8"), msg, hashlib.sha256).digest()
        actual_sig = _b64decode(sig_b64)
        if not hmac.compare_digest(expected_sig, actual_sig):
            return None
        payload = json.loads(_b64decode(payload_b64).decode("utf-8"))
        if payload.get("exp", 0) < int(time.time()):
            return None
        return payload
    except Exception:
        return None

async def get_current_user(creds: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer)) -> dict:
    """FastAPI dependency to extract and validate the authenticated user."""
    if not creds or not creds.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token required. Please sign in.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_access_token(creds.credentials)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication session. Please sign in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    with db.connect() as c:
        row = c.execute("SELECT id, email, full_name, is_verified, created_at FROM users WHERE id=?", (payload["sub"],)).fetchone()
        if not row:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account no longer exists.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        user = dict(row)
        if not user.get("is_verified"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Email address has not been verified. Please verify your email first.",
            )
        return user
