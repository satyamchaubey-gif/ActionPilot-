import os, smtplib, secrets, logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone, timedelta
from . import db

logger = logging.getLogger("actionpilot.email")

def now_utc():
    return datetime.now(timezone.utc)

def generate_otp() -> str:
    """Generate a secure 6-digit verification code."""
    # Ensure first digit is not 0 for clear readability
    first = secrets.choice("123456789")
    rest = "".join(secrets.choice("0123456789") for _ in range(5))
    return f"{first}{rest}"

def store_verification_code(user_id: str, email: str, code: str, minutes: int = 15) -> datetime:
    """Save code to DB and expire previous unused codes for this email."""
    normalized_email = email.lower().strip()
    expires_at = now_utc() + timedelta(minutes=minutes)
    with db.connect() as c:
        # Mark previous codes as used
        c.execute("UPDATE verification_codes SET used=1 WHERE email=? AND used=0", (normalized_email,))
        c.execute(
            """INSERT INTO verification_codes(user_id, email, code, expires_at, used, created_at)
               VALUES(?, ?, ?, ?, 0, ?)""",
            (user_id, normalized_email, code, expires_at.isoformat(), now_utc().isoformat()),
        )
    return expires_at

def verify_code(email: str, code: str) -> bool:
    """Validate verification code from DB."""
    normalized_email = email.lower().strip()
    clean_code = code.strip()
    current_time = now_utc().isoformat()
    with db.connect() as c:
        row = c.execute(
            """SELECT id, user_id FROM verification_codes
               WHERE email=? AND code=? AND used=0 AND expires_at > ?
               ORDER BY id DESC LIMIT 1""",
            (normalized_email, clean_code, current_time),
        ).fetchone()
        if not row:
            return False
        # Mark as used
        c.execute("UPDATE verification_codes SET used=1 WHERE id=?", (row["id"],))
        return True

def send_verification_email(to_email: str, code: str, user_name: str = "") -> dict:
    """
    Send verification email via Gmail SMTP if credentials exist,
    otherwise fallback cleanly to console log in development.
    """
    normalized_email = to_email.lower().strip()
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com").strip()
    smtp_port = int(os.getenv("SMTP_PORT", "587").strip())
    smtp_user = os.getenv("SMTP_USER", os.getenv("GMAIL_USER", "")).strip()
    smtp_pass = os.getenv("SMTP_PASS", os.getenv("GMAIL_APP_PASSWORD", "")).strip().replace(" ", "")
    smtp_from = os.getenv("SMTP_FROM", smtp_user or "ActionPilot <noreply@actionpilot.app>").strip()

    name_greeting = f"Hi {user_name}," if user_name else "Hello,"

    # If SMTP credentials are configured, attempt to send real email
    if smtp_user and smtp_pass:
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"ActionPilot — Verify your email ({code})"
            msg["From"] = smtp_from
            msg["To"] = normalized_email

            plain_text = f"""{name_greeting}

Welcome to ActionPilot!

Your email verification code is: {code}

This code will expire in 15 minutes.
If you did not request this verification code, please ignore this email.

— ActionPilot Team
"""
            html_text = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>ActionPilot Verification</title>
</head>
<body style="margin:0;padding:24px;background-color:#0f172a;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;color:#e2e8f0;">
  <table width="100%" border="0" cellspacing="0" cellpadding="0" style="max-width:540px;margin:0 auto;background:#1e293b;border-radius:12px;border:1px solid #334155;overflow:hidden;">
    <tr>
      <td style="padding:28px 32px;background:linear-gradient(135deg,#1e1b4b,#312e81);border-bottom:1px solid #4338ca;">
        <table width="100%" border="0" cellspacing="0" cellpadding="0">
          <tr>
            <td>
              <span style="font-size:20px;font-weight:800;color:#ffffff;letter-spacing:-0.5px;">action<span style="color:#818cf8;">pilot</span></span>
              <div style="font-size:11px;color:#c7d2fe;margin-top:3px;letter-spacing:1px;text-transform:uppercase;">Evidence-Driven AI Orchestration</div>
            </td>
          </tr>
        </table>
      </td>
    </tr>
    <tr>
      <td style="padding:32px;">
        <h2 style="font-size:18px;font-weight:700;color:#f8fafc;margin:0 0 12px 0;">{name_greeting}</h2>
        <p style="font-size:14px;line-height:1.6;color:#94a3b8;margin:0 0 24px 0;">
          Thank you for signing up for ActionPilot. Please enter this 6-digit verification code to confirm your email and activate your workspace:
        </p>
        <div style="text-align:center;margin:28px 0;padding:20px;background:#0f172a;border:1px solid #3b82f6;border-radius:10px;">
          <span style="font-size:32px;font-weight:800;letter-spacing:8px;color:#60a5fa;font-family:monospace;">{code}</span>
        </div>
        <p style="font-size:12px;color:#64748b;line-height:1.5;margin:0 0 16px 0;">
          ⏱️ This code will expire in <strong>15 minutes</strong>.<br>
          If you didn't create an ActionPilot account, you can safely disregard this email.
        </p>
      </td>
    </tr>
    <tr>
      <td style="padding:16px 32px;background:#0f172a;border-top:1px solid #334155;text-align:center;font-size:11px;color:#475569;">
        ActionPilot Workspace Intelligence &copy; {datetime.now().year}
      </td>
    </tr>
  </table>
</body>
</html>"""
            msg.attach(MIMEText(plain_text, "plain"))
            msg.attach(MIMEText(html_text, "html"))

            with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(smtp_user, smtp_pass)
                server.sendmail(smtp_from, [normalized_email], msg.as_string())

            logger.info("Verification email successfully sent to %s via SMTP", normalized_email)
            return {"sent": True, "provider": "gmail_smtp"}
        except Exception as e:
            logger.error("Failed to send verification email via SMTP: %s", e)
            print(f"\n[ActionPilot WARNING] Failed to send email via SMTP ({e}). Falling back to console output.")

    # Fallback to console output (development / when SMTP not configured)
    banner = f"""
================================================================================
  [ActionPilot] GMAIL VERIFICATION CODE
  Recipient: {normalized_email}
  Verification Code: [ {code} ]
  Expires in: 15 minutes
  Note: To send real emails, set SMTP_USER and SMTP_PASS (Gmail App Password)
        in backend/.env
================================================================================
"""
    print(banner)
    return {"sent": False, "provider": "dev_console", "dev_code": code}
