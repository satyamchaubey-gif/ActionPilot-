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
    with db.connect() as c:
        c.execute("DELETE FROM audit_events")
        c.execute("DELETE FROM tasks")
        c.execute("DELETE FROM documents")
        c.execute("DELETE FROM verification_codes")
        c.execute("DELETE FROM users")

def test_full_auth_flow():
    client = TestClient(app)

    # 1. Signup
    res = client.post("/api/auth/signup", json={"email": "alice@example.com", "password": "password123", "full_name": "Alice"})
    assert res.status_code == 200
    data = res.json()
    assert data["requires_verification"] is True
    code = data.get("dev_code")
    assert code is not None and len(code) == 6

    # 2. Try login before verification -> should require verification
    login_unverified = client.post("/api/auth/login", json={"email": "alice@example.com", "password": "password123"})
    assert login_unverified.status_code == 200
    assert login_unverified.json()["requires_verification"] is True
    # The login call sent a fresh code
    code = login_unverified.json().get("dev_code") or code

    # 3. Verify with wrong code -> 400
    wrong_res = client.post("/api/auth/verify-email", json={"email": "alice@example.com", "code": "000000"})
    assert wrong_res.status_code == 400

    # 4. Verify with correct code -> 200 and token returned
    verify_res = client.post("/api/auth/verify-email", json={"email": "alice@example.com", "code": code})
    assert verify_res.status_code == 200
    token = verify_res.json()["token"]
    assert token is not None

    # 5. Access /api/auth/me
    headers = {"Authorization": f"Bearer {token}"}
    me_res = client.get("/api/auth/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "alice@example.com"
    assert me_res.json()["full_name"] == "Alice"

    # 6. Subsequent login
    login_res = client.post("/api/auth/login", json={"email": "alice@example.com", "password": "password123"})
    assert login_res.status_code == 200
    assert login_res.json()["token"] is not None

def test_user_data_isolation():
    client = TestClient(app)

    # Register & verify Alice
    r_a = client.post("/api/auth/signup", json={"email": "alice@corp.com", "password": "password123", "full_name": "Alice"})
    t_a = client.post("/api/auth/verify-email", json={"email": "alice@corp.com", "code": r_a.json()["dev_code"]}).json()["token"]
    h_a = {"Authorization": f"Bearer {t_a}"}

    # Register & verify Bob
    r_b = client.post("/api/auth/signup", json={"email": "bob@corp.com", "password": "password456", "full_name": "Bob"})
    t_b = client.post("/api/auth/verify-email", json={"email": "bob@corp.com", "code": r_b.json()["dev_code"]}).json()["token"]
    h_b = {"Authorization": f"Bearer {t_b}"}

    # Alice uploads document
    ingest_res = client.post("/api/documents/text", json={"title": "Alice Strategy", "text": "Action: Alice must deliver Q4 roadmap by 2026-11-15."}, headers=h_a)
    assert ingest_res.status_code == 200

    # Alice has 1 document and 1 task
    alice_docs = client.get("/api/documents", headers=h_a).json()
    alice_tasks = client.get("/api/tasks", headers=h_a).json()
    assert len(alice_docs) == 1
    assert len(alice_tasks) == 1

    # Bob has 0 documents and 0 tasks
    bob_docs = client.get("/api/documents", headers=h_b).json()
    bob_tasks = client.get("/api/tasks", headers=h_b).json()
    assert len(bob_docs) == 0
    assert len(bob_tasks) == 0

    # Bob cannot access or approve Alice's task
    alice_task_id = alice_tasks[0]["id"]
    forbidden_approve = client.post(f"/api/tasks/{alice_task_id}/approve", headers=h_b)
    assert forbidden_approve.status_code == 404
