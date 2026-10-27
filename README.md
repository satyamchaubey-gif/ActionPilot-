# ActionPilot — Evidence-Driven AI Workflow Automation

Runnable App: React + TypeScript frontend, FastAPI backend, SQLite persistence, user authentication with Gmail verification, voice memo ingestion, evidence-linked extraction, AI conflict resolution, human approval, and 1-click external action dispatching (Google Calendar, Slack, Discord, GitHub).

## Run it
Requirements: Python 3.10+ and Node.js 18+.

Terminal 1 (Backend):
```bash
cd backend
source .venv/bin/activate  # Windows: .venv\Scripts\activate
uvicorn app.main:app --reload --port 8000
```

Terminal 2 (Frontend):
```bash
cd frontend
npm run dev
```

Open http://localhost:5173. API docs: http://127.0.0.1:8000/docs.

---

## 🏆 Top 5 Hackathon Features (Implemented)

### 1. 🎙️ Live Voice / Meeting Note Recording
- Click **"Record Note"** in the topbar or in the New Workflow modal.
- Uses browser Web Speech API for real-time speech-to-text streaming.
- Pulsing recording indicator with live transcription box.
- 1-click stop & extract actions directly from voice memos!

### 2. ⚡ 1-Click "Demo Scenario" Quick-Loader (Failsafe Live Pitch)
- Click **"⚡ Load Demo Scenario ▾"** in the topbar to test 3 realistic scenarios in 1 second:
  - **Product Launch Sync**: Priya deadline contradiction (Nov 2 vs Nov 6).
  - **Security Incident Response**: Critical API credential leak with missing assignees.
  - **Executive Strategy Offsite**: Budget signoff revisions and vendor RFP deadlines.

### 3. 📄 Interactive Side-by-Side Evidence Highlighting
- Click **"View in Source Context"** on any task proposal or quote.
- Opens the **Source Text Inspector** with the exact evidence excerpt highlighted with a radiant amber marker (`<mark>`).
- Guarantees zero hallucinations and proves provenance to users and auditors.

### 4. 🧠 Interactive "AI Conflict Resolver"
- When conflicting deadlines or instructions occur (e.g. initial meeting notes vs client updates), ActionPilot flags the conflict.
- Click **"⚡ Resolve with AI"**:
  - Compares the contradictory dates side by side.
  - Displays AI context recommendation (e.g., *"Client update overrides earlier internal draft"*).
  - 1-click adoption of the resolved date with automated audit trail logging!

### 5. 🚀 "One-Click Dispatch" External Integrations (Close the Loop)
- Once a task is approved by a human, click **"Dispatch Action"**:
  - **Google Calendar 📅**: Generates a pre-filled Google Calendar event URL with title, date, description, and evidence.
  - **Slack / Discord 💬**: Dispatches formatted payload to webhook URL (or simulated dry-run).
  - **GitHub Issue 🐙**: Pre-fills a new GitHub issue with markdown template and verification signatures.
  - **Email ✉️**: Dispatches notification to assignee.
- Includes a **Dry-Run Simulation Toggle** for risk-free hackathon demos.

---

## Authentication & Multi-User Separation
- **Sign In / Sign Up**: App starts on the Sign In / Sign Up page.
- **Tenant Isolation**: Every user gets their own private workspace.
- **Gmail / Email Verification**: 6-digit OTP code with development auto-fill badge.

### 👤 Pre-Loaded Demo Accounts with Sample Scenarios
ActionPilot auto-seeds full sample scenarios into the workspace for immediate evaluation:
- **Demo Account Email**: `satyamchaubey471@gmail.com` (or `satayamchaubey471@gmail.com` / `judge@hackathon.com`)
- **Password**: `password123`
- **Included Scenarios**:
  - **Product Launch Sync (Q4)**: Conflicting client deadlines (Nov 2 vs Nov 6), onboarding checklist draft, and Google Calendar dispatched FAQ.
  - **Security Incident Response (Sev-1)**: Accelerated API credential rotation deadline, VPC egress audit task, and Slack webhook dispatch.
  - **Executive Offsite & Strategy**: Board committee budget revision, vendor RFP evaluation dispatched to GitHub, and keynote logistics.
  - **Multilingual Voice Studio Notes**: 3 recorded Hinglish & English voice memos with live speaker transcripts.
  - **Immutable Audit Trail**: Chronological ledger of all ingestions, extractions, conflict flags, approvals, and dispatches.
