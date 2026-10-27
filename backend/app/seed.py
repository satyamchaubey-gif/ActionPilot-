import json, hashlib, uuid
from datetime import datetime, timezone

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

DEMO_PASSWORD_HASH = "pbkdf2:sha256:100000:fd052e4409164df363712ecf694269db:c386ce1b0fd4bb0b99d7153714fc4df88163903b00ee9a45dd2a77107d01a285"  # password123

TARGET_USERS = [
    {
        "id": "usr_satyam_chaubey",
        "email": "satyamchaubey471@gmail.com",
        "full_name": "Satyam Chaubey",
        "contact_no": "+91 9876543210",
        "age": 25,
        "job_title": "Lead AI Engineer & Product Architect",
        "preferences": {"theme": "dark", "email_notifications": True, "auto_extract": True},
    },
    {
        "id": "usr_satayam_chaubey",
        "email": "satayamchaubey471@gmail.com",
        "full_name": "Satyam Chaubey",
        "contact_no": "+91 9876543210",
        "age": 25,
        "job_title": "Lead AI Engineer & Product Architect",
        "preferences": {"theme": "dark", "email_notifications": True, "auto_extract": True},
    },
    {
        "id": "usr_demo_judge_2026",
        "email": "judge@hackathon.com",
        "full_name": "Hackathon Judge",
        "contact_no": "+1 555-0199",
        "age": 32,
        "job_title": "Senior AI Systems Evaluator",
        "preferences": {"theme": "dark", "email_notifications": True, "auto_extract": True},
    }
]

SCENARIOS = [
    {
        "key": "product_launch",
        "title": "Product Launch Sync — 2026 Q4",
        "filename": "product_launch_sync.txt",
        "content": (
            "Product launch sync — meeting notes\n\n"
            "Action: Priya must send the launch plan by 2026-11-02. This is high priority.\n"
            "Action: Priya must send the launch plan by 2026-11-06. Updated note from the client says the plan is due on the later date.\n"
            "Please review the onboarding checklist by 2026-11-05.\n"
            "Owner: Daniel — publish the support FAQ by 2026-11-08.\n"
            "The team discussed the design refresh and agreed to revisit the topic next week."
        ),
        "tasks": [
            {
                "title": "Priya must send the launch plan by 2026-11-06.",
                "description": "Client update moved launch plan deadline to Nov 6. High priority delivery.",
                "assignee": "Priya",
                "due_date": "2026-11-06",
                "priority": "high",
                "confidence": 0.95,
                "status": "proposed",
                "uncertainty_flags": [
                    "Potential deadline conflict with another instruction (2026-11-02 vs 2026-11-06); human review required."
                ],
                "evidence": [
                    {
                        "quote": "Action: Priya must send the launch plan by 2026-11-06. Updated note from the client says the plan is due on the later date.",
                        "start": 115,
                        "end": 238,
                        "source_name": "product_launch_sync.txt"
                    }
                ],
                "draft": None,
                "dispatched": 0,
                "dispatched_at": None,
                "dispatch_channel": None
            },
            {
                "title": "Please review the onboarding checklist by 2026-11-05.",
                "description": "Validate onboarding checklist for Q4 customer cohort.",
                "assignee": "Priya",
                "due_date": "2026-11-05",
                "priority": "medium",
                "confidence": 0.90,
                "status": "approved",
                "uncertainty_flags": [],
                "evidence": [
                    {
                        "quote": "Please review the onboarding checklist by 2026-11-05.",
                        "start": 239,
                        "end": 292,
                        "source_name": "product_launch_sync.txt"
                    }
                ],
                "draft": {
                    "channel": "email",
                    "recipient": "priya@example.com",
                    "subject": "Review Onboarding Checklist by Nov 5",
                    "body": "Hi Priya, please ensure the onboarding checklist is reviewed by Nov 5 as agreed in the sync.",
                    "created_at": "2026-10-26T10:00:00+00:00",
                    "sent": False
                },
                "dispatched": 0,
                "dispatched_at": None,
                "dispatch_channel": None
            },
            {
                "title": "Owner: Daniel — publish the support FAQ by 2026-11-08.",
                "description": "Publish comprehensive customer support FAQ ahead of release.",
                "assignee": "Daniel",
                "due_date": "2026-11-08",
                "priority": "high",
                "confidence": 0.98,
                "status": "approved",
                "uncertainty_flags": [],
                "evidence": [
                    {
                        "quote": "Owner: Daniel — publish the support FAQ by 2026-11-08.",
                        "start": 293,
                        "end": 347,
                        "source_name": "product_launch_sync.txt"
                    }
                ],
                "draft": None,
                "dispatched": 1,
                "dispatched_at": "2026-10-26T11:00:00+00:00",
                "dispatch_channel": "calendar"
            }
        ]
    },
    {
        "key": "security_incident",
        "title": "Security Incident Brief — Sev 1 DB Access",
        "filename": "security_incident_response.txt",
        "content": (
            "Incident Response Call — Severity 1 Alert\n\n"
            "URGENT Action: DevSecOps team must rotate the compromised API credentials by 2026-10-24. Blocker for deployment.\n"
            "URGENT Action: DevSecOps team must rotate the compromised API credentials by 2026-10-23. Security lead confirmed rotation deadline was moved up.\n"
            "Action: Please audit VPC egress traffic logs by 2026-10-25.\n"
            "Owner: Rahul — notify external SOC audit partners by 2026-10-26.\n"
            "Security team recommends enforcing MFA across all tenant accounts."
        ),
        "tasks": [
            {
                "title": "DevSecOps team must rotate the compromised API credentials by 2026-10-23",
                "description": "Security lead confirmed rotation deadline was moved up. Blocker for deployment.",
                "assignee": "DevSecOps Team",
                "due_date": "2026-10-23",
                "priority": "urgent",
                "confidence": 0.98,
                "status": "approved",
                "uncertainty_flags": [
                    "Potential deadline conflict with another instruction (2026-10-24 vs 2026-10-23); human review required."
                ],
                "evidence": [
                    {
                        "quote": "URGENT Action: DevSecOps team must rotate the compromised API credentials by 2026-10-23. Security lead confirmed rotation deadline was moved up.",
                        "start": 156,
                        "end": 300,
                        "source_name": "security_incident_response.txt"
                    }
                ],
                "draft": None,
                "dispatched": 0,
                "dispatched_at": None,
                "dispatch_channel": None
            },
            {
                "title": "Action: Please audit VPC egress traffic logs by 2026-10-25.",
                "description": "Deep dive packet inspection on VPC egress logs during incident window.",
                "assignee": "DevSecOps Team",
                "due_date": "2026-10-25",
                "priority": "high",
                "confidence": 0.92,
                "status": "proposed",
                "uncertainty_flags": [],
                "evidence": [
                    {
                        "quote": "Action: Please audit VPC egress traffic logs by 2026-10-25.",
                        "start": 301,
                        "end": 360,
                        "source_name": "security_incident_response.txt"
                    }
                ],
                "draft": None,
                "dispatched": 0,
                "dispatched_at": None,
                "dispatch_channel": None
            },
            {
                "title": "Owner: Rahul — notify external SOC audit partners by 2026-10-26.",
                "description": "Formal notification to SOC audit partners regarding incident containment.",
                "assignee": "Rahul",
                "due_date": "2026-10-26",
                "priority": "urgent",
                "confidence": 0.96,
                "status": "approved",
                "uncertainty_flags": [],
                "evidence": [
                    {
                        "quote": "Owner: Rahul — notify external SOC audit partners by 2026-10-26.",
                        "start": 361,
                        "end": 425,
                        "source_name": "security_incident_response.txt"
                    }
                ],
                "draft": None,
                "dispatched": 1,
                "dispatched_at": "2026-10-26T12:00:00+00:00",
                "dispatch_channel": "slack"
            }
        ]
    },
    {
        "key": "exec_offsite",
        "title": "Executive Offsite & Budget Alignment",
        "filename": "q4_strategy_offsite.txt",
        "content": (
            "Q4 Executive Strategy Offsite — Leadership Notes\n\n"
            "Action: Finance director must submit the finalized FY27 budget model by 2026-11-12. Critical priority.\n"
            "Action: Finance director must submit the finalized FY27 budget model by 2026-11-18. Revised after board subcommittee review.\n"
            "Action: Review vendor RFP proposals for AI infrastructure by 2026-11-15.\n"
            "Owner: Sarah — confirm keynote speaker travel itinerary by 2026-11-20.\n"
            "Team agreed on prioritizing customer retention over aggressive expansion."
        ),
        "tasks": [
            {
                "title": "Action: Finance director must submit the finalized FY27 budget model by 2026-11-18.",
                "description": "Revised board subcommittee model submission for FY27 budget.",
                "assignee": "Finance Director",
                "due_date": "2026-11-18",
                "priority": "urgent",
                "confidence": 0.94,
                "status": "proposed",
                "uncertainty_flags": [
                    "Potential deadline conflict with another instruction (2026-11-12 vs 2026-11-18); human review required."
                ],
                "evidence": [
                    {
                        "quote": "Action: Finance director must submit the finalized FY27 budget model by 2026-11-18. Revised after board subcommittee review.",
                        "start": 153,
                        "end": 277,
                        "source_name": "q4_strategy_offsite.txt"
                    }
                ],
                "draft": None,
                "dispatched": 0,
                "dispatched_at": None,
                "dispatch_channel": None
            },
            {
                "title": "Action: Review vendor RFP proposals for AI infrastructure by 2026-11-15.",
                "description": "Evaluate GPU cluster vendor proposals and SLA guarantees.",
                "assignee": "Sarah",
                "due_date": "2026-11-15",
                "priority": "high",
                "confidence": 0.91,
                "status": "approved",
                "uncertainty_flags": [],
                "evidence": [
                    {
                        "quote": "Action: Review vendor RFP proposals for AI infrastructure by 2026-11-15.",
                        "start": 278,
                        "end": 350,
                        "source_name": "q4_strategy_offsite.txt"
                    }
                ],
                "draft": None,
                "dispatched": 1,
                "dispatched_at": "2026-10-26T14:30:00+00:00",
                "dispatch_channel": "github"
            },
            {
                "title": "Owner: Sarah — confirm keynote speaker travel itinerary by 2026-11-20.",
                "description": "Logistics, flights, and venue coordination for keynote speaker.",
                "assignee": "Sarah",
                "due_date": "2026-11-20",
                "priority": "medium",
                "confidence": 0.88,
                "status": "proposed",
                "uncertainty_flags": [],
                "evidence": [
                    {
                        "quote": "Owner: Sarah — confirm keynote speaker travel itinerary by 2026-11-20.",
                        "start": 351,
                        "end": 421,
                        "source_name": "q4_strategy_offsite.txt"
                    }
                ],
                "draft": None,
                "dispatched": 0,
                "dispatched_at": None,
                "dispatch_channel": None
            }
        ]
    }
]

MEETINGS = [
    {
        "title": "Q4 Sprint Planning & Architecture Alignment (Hinglish)",
        "recorded_at": "2026-10-26T15:30:00+00:00",
        "duration_seconds": 245,
        "speakers": ["Alex", "Priya"],
        "transcript": "Alex: Let's sync on Q4 release targets. Priya, what is your delivery timeline for the marketing deck? Priya: Priya ko kal tak revised launch plan aur marketing deck submit karna hai. Alex: Perfect, Alex Friday tak deployment script verify karke deploy karega.",
        "task_count": 2
    },
    {
        "title": "Emergency Sev-1 Database Latency Call",
        "recorded_at": "2026-10-26T16:45:00+00:00",
        "duration_seconds": 182,
        "speakers": ["Alex", "Rohan"],
        "transcript": "Alex: Emergency incident response meeting: production database latency high ho gaya hai. Alex abhi sare compromised API keys revoke karega. Rohan: Rohan post-mortem meeting 2026-11-04 tak schedule karega aur client report share karega.",
        "task_count": 2
    },
    {
        "title": "Executive Strategy & Vendor RFP Review",
        "recorded_at": "2026-10-27T09:15:00+00:00",
        "duration_seconds": 310,
        "speakers": ["Sarah", "Ananya"],
        "transcript": "Sarah: Moving to executive strategy: will vendor proposals be completed this month? Sarah ko vendor RFP proposals Monday tak finalize karke submit karna hai, aur Ananya Q4 budget review complete karegi.",
        "task_count": 2
    }
]

def seed_user_scenarios(cursor, user_id: str, user_email: str):
    """
    Idempotently seeds all sample scenarios, tasks, meetings, and audit events for a given user.
    """
    # 1. Documents & Tasks
    for sc in SCENARIOS:
        content_hash = sha256_text(f"{user_id}:{sc['key']}:{sc['content']}")
        existing_doc = cursor.execute(
            "SELECT id FROM documents WHERE user_id=? AND title=?",
            (user_id, sc["title"])
        ).fetchone()

        if existing_doc:
            doc_id = existing_doc[0] if isinstance(existing_doc, (list, tuple)) else existing_doc["id"]
        else:
            doc_id = str(uuid.uuid4())
            ts = now_iso()
            cursor.execute(
                """INSERT INTO documents(id, user_id, title, filename, content, content_hash, created_at, status)
                   VALUES(?, ?, ?, ?, ?, ?, ?, ?)""",
                (doc_id, user_id, sc["title"], sc["filename"], sc["content"], content_hash, ts, "processed")
            )
            cursor.execute(
                """INSERT INTO audit_events(user_id, entity_type, entity_id, event_type, actor, details, created_at)
                   VALUES(?, ?, ?, ?, ?, ?, ?)""",
                (user_id, "document", doc_id, "document_ingested", user_email, json.dumps({"title": sc["title"], "sha256": content_hash}), ts)
            )

        # Ensure tasks exist for this document
        existing_tasks = cursor.execute(
            "SELECT count(*) FROM tasks WHERE user_id=? AND document_id=?",
            (user_id, doc_id)
        ).fetchone()[0]

        if existing_tasks == 0:
            for t in sc["tasks"]:
                task_id = str(uuid.uuid4())
                ts = now_iso()
                draft_json = json.dumps(t["draft"]) if t.get("draft") else None
                cursor.execute(
                    """INSERT INTO tasks(
                        id, user_id, document_id, title, description, assignee, due_date,
                        priority, dependencies, evidence, confidence, uncertainty_flags,
                        status, draft, dispatched, dispatched_at, dispatch_channel,
                        created_at, updated_at
                    ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        task_id, user_id, doc_id, t["title"], t["description"], t["assignee"], t["due_date"],
                        t["priority"], "[]", json.dumps(t["evidence"]), t["confidence"],
                        json.dumps(t["uncertainty_flags"]), t["status"], draft_json,
                        t["dispatched"], t["dispatched_at"], t["dispatch_channel"],
                        ts, ts
                    )
                )

                cursor.execute(
                    """INSERT INTO audit_events(user_id, entity_type, entity_id, event_type, actor, details, created_at)
                       VALUES(?, ?, ?, ?, ?, ?, ?)""",
                    (user_id, "task", task_id, "task_proposed", user_email, json.dumps({"title": t["title"], "confidence": t["confidence"]}), ts)
                )

                if t["status"] == "approved":
                    cursor.execute(
                        """INSERT INTO audit_events(user_id, entity_type, entity_id, event_type, actor, details, created_at)
                           VALUES(?, ?, ?, ?, ?, ?, ?)""",
                        (user_id, "task", task_id, "task_approved", user_email, json.dumps({"title": t["title"], "auto_verified": True}), ts)
                    )

                if t["dispatched"]:
                    cursor.execute(
                        """INSERT INTO audit_events(user_id, entity_type, entity_id, event_type, actor, details, created_at)
                           VALUES(?, ?, ?, ?, ?, ?, ?)""",
                        (user_id, "task", task_id, "action_dispatched", user_email, json.dumps({"channel": t["dispatch_channel"], "target": "demo"}), t["dispatched_at"] or ts)
                    )

    # 2. Meetings
    existing_meetings_count = cursor.execute(
        "SELECT count(*) FROM meetings WHERE user_id=?",
        (user_id,)
    ).fetchone()[0]

    if existing_meetings_count == 0:
        for m in MEETINGS:
            meet_id = str(uuid.uuid4())
            cursor.execute(
                """INSERT INTO meetings(id, user_id, title, recorded_at, duration_seconds, transcript, speakers, task_count, created_at)
                   VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    meet_id, user_id, m["title"], m["recorded_at"],
                    m["duration_seconds"], m["transcript"], json.dumps(m["speakers"]),
                    m["task_count"], m["recorded_at"]
                )
            )
            cursor.execute(
                """INSERT INTO audit_events(user_id, entity_type, entity_id, event_type, actor, details, created_at)
                   VALUES(?, ?, ?, ?, ?, ?, ?)""",
                (user_id, "meeting", meet_id, "meeting_recorded", user_email, json.dumps({"title": m["title"], "duration": m["duration_seconds"]}), m["recorded_at"])
            )

def seed_all_demo_users(cursor):
    """
    Ensures all demo users exist and have full sample scenarios populated.
    """
    now = now_iso()
    for u in TARGET_USERS:
        email = u["email"].lower().strip()
        existing = cursor.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
        if existing:
            user_id = existing[0] if isinstance(existing, (list, tuple)) else existing["id"]
            cursor.execute(
                "UPDATE users SET full_name=?, contact_no=?, age=?, job_title=?, preferences=?, is_verified=1 WHERE id=?",
                (u["full_name"], u["contact_no"], u["age"], u["job_title"], json.dumps(u["preferences"]), user_id)
            )
        else:
            user_id = u["id"]
            cursor.execute(
                """INSERT INTO users(id, email, password_hash, full_name, contact_no, age, job_title, preferences, is_verified, created_at)
                   VALUES(?, ?, ?, ?, ?, ?, ?, ?, 1, ?)""",
                (
                    user_id, email, DEMO_PASSWORD_HASH, u["full_name"],
                    u["contact_no"], u["age"], u["job_title"], json.dumps(u["preferences"]),
                    now
                )
            )
        seed_user_scenarios(cursor, user_id, email)
