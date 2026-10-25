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
        c.execute("DELETE FROM meetings")
        c.execute("DELETE FROM users")
    yield

def test_profile_update_and_meetings_history():
    client = TestClient(app)

    # 1. Sign up user
    r_signup = client.post("/api/auth/signup", json={"email": "prof@example.com", "password": "password123", "full_name": "Original Name"})
    code = r_signup.json().get("dev_code")
    token = client.post("/api/auth/verify-email", json={"email": "prof@example.com", "code": code}).json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Update profile (contact_no, age, job_title, preferences)
    r_patch = client.patch(
        "/api/auth/profile",
        json={
            "full_name": "Updated Lead",
            "contact_no": "+91 9876543210",
            "age": 28,
            "job_title": "Staff Architect",
            "preferences": {"theme": "dark", "multi_speaker_mode": True}
        },
        headers=headers
    )
    assert r_patch.status_code == 200
    user_data = r_patch.json()["user"]
    assert user_data["full_name"] == "Updated Lead"
    assert user_data["contact_no"] == "+91 9876543210"
    assert user_data["age"] == 28
    assert user_data["job_title"] == "Staff Architect"
    assert user_data["preferences"]["multi_speaker_mode"] is True

    # 3. Create a meeting note in History
    r_meeting = client.post(
        "/api/meetings",
        json={
            "title": "Sprint Planning Q4",
            "transcript": "Speaker 1 (Alex): We must finalize the API schema by 2026-11-02. Speaker 2 (Sarah): I will deploy the auth service by 2026-11-03.",
            "duration_seconds": 185,
            "speakers": ["Speaker 1 (Alex)", "Speaker 2 (Sarah)"],
            "auto_extract_tasks": True
        },
        headers=headers
    )
    assert r_meeting.status_code == 200
    m_data = r_meeting.json()
    assert m_data["title"] == "Sprint Planning Q4"
    assert len(m_data["speakers"]) == 2
    assert m_data["task_count"] > 0

    # 4. List meetings in History
    r_list = client.get("/api/meetings", headers=headers)
    assert r_list.status_code == 200
    meetings = r_list.json()
    assert len(meetings) == 1
    assert meetings[0]["title"] == "Sprint Planning Q4"

    # 5. Delete meeting
    mid = meetings[0]["id"]
    r_del = client.delete(f"/api/meetings/{mid}", headers=headers)
    assert r_del.status_code == 200
    assert len(client.get("/api/meetings", headers=headers).json()) == 0
