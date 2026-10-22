import pytest
from fastapi.testclient import TestClient
from app.main import app
from app import db

@pytest.fixture(autouse=True)
def clean_database():
    with db.connect() as c:
        c.execute("DELETE FROM audit_events")
        c.execute("DELETE FROM tasks")
        c.execute("DELETE FROM documents")
        c.execute("DELETE FROM verification_codes")
        c.execute("DELETE FROM users")
    yield

def test_demo_preset_and_conflict_resolution():
    client = TestClient(app)

    # 1. Register test user
    r_signup = client.post("/api/auth/signup", json={"email": "judge@hackathon.com", "password": "password123", "full_name": "Judge"})
    code = r_signup.json().get("dev_code")
    token = client.post("/api/auth/verify-email", json={"email": "judge@hackathon.com", "code": code}).json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Load Demo Scenario
    r_demo = client.post("/api/demo/preset", json={"preset_id": "product_launch"}, headers=headers)
    assert r_demo.status_code == 200
    assert "document_id" in r_demo.json()

    # 3. Fetch Tasks
    tasks = client.get("/api/tasks", headers=headers).json()
    assert len(tasks) > 0

    # 4. Find task with deadline conflict
    conflict_task = next(t for t in tasks if any("conflict" in f.lower() for f in t["uncertainty_flags"]))
    tid = conflict_task["id"]

    # 5. Resolve Conflict
    r_resolve = client.post(
        f"/api/tasks/{tid}/resolve-conflict",
        json={"resolved_due_date": "2026-11-06", "rationale": "Adopted client confirmation"},
        headers=headers
    )
    assert r_resolve.status_code == 200
    assert r_resolve.json()["due_date"] == "2026-11-06"
    assert not any("conflict" in f.lower() for f in r_resolve.json()["uncertainty_flags"])

    # 6. Approve Task
    r_app = client.post(f"/api/tasks/{tid}/approve", headers=headers)
    assert r_app.status_code == 200

    # 7. Dispatch to Google Calendar
    r_dispatch_cal = client.post(
        f"/api/tasks/{tid}/dispatch",
        json={"channel": "calendar", "simulate": True},
        headers=headers
    )
    assert r_dispatch_cal.status_code == 200
    assert "calendar_url" in r_dispatch_cal.json()["dispatch"]

    # 8. Dispatch to Slack (Simulated Webhook)
    r_dispatch_slack = client.post(
        f"/api/tasks/{tid}/dispatch",
        json={"channel": "slack", "simulate": True},
        headers=headers
    )
    assert r_dispatch_slack.status_code == 200
    assert r_dispatch_slack.json()["dispatch"]["simulated"] is True
