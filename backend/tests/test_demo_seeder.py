import pytest
from fastapi.testclient import TestClient
from app.main import app
from app import db
from app.seed import seed_all_demo_users

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

def test_satyam_chaubey_sample_scenarios():
    client = TestClient(app)

    # 1. Manually run seeder
    with db.connect() as c:
        seed_all_demo_users(c)

    # 2. Test login for satyamchaubey471@gmail.com
    r_login1 = client.post("/api/auth/login", json={
        "email": "satyamchaubey471@gmail.com",
        "password": "password123"
    })
    assert r_login1.status_code == 200, f"Login failed: {r_login1.text}"
    data1 = r_login1.json()
    token1 = data1["token"]
    assert token1 is not None
    assert data1["user"]["full_name"] == "Satyam Chaubey"

    headers1 = {"Authorization": f"Bearer {token1}"}

    # Verify tasks, documents, meetings, and audit for satyamchaubey471@gmail.com
    tasks1 = client.get("/api/tasks", headers=headers1).json()
    assert len(tasks1) == 9
    assert any(any("conflict" in f.lower() for f in t["uncertainty_flags"]) for t in tasks1)
    assert any(t["dispatched"] == 1 for t in tasks1)

    docs1 = client.get("/api/documents", headers=headers1).json()
    assert len(docs1) == 3

    meetings1 = client.get("/api/meetings", headers=headers1).json()
    assert len(meetings1) == 3

    audit1 = client.get("/api/audit", headers=headers1).json()
    assert len(audit1) > 0

    # 3. Test login for satayamchaubey471@gmail.com (explicit user query variant)
    r_login2 = client.post("/api/auth/login", json={
        "email": "satayamchaubey471@gmail.com",
        "password": "password123"
    })
    assert r_login2.status_code == 200, f"Login failed: {r_login2.text}"
    token2 = r_login2.json()["token"]
    assert token2 is not None

    headers2 = {"Authorization": f"Bearer {token2}"}
    tasks2 = client.get("/api/tasks", headers=headers2).json()
    assert len(tasks2) == 9

    docs2 = client.get("/api/documents", headers=headers2).json()
    assert len(docs2) == 3
