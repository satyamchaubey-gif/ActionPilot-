from datetime import date
from typing import Literal, Optional
from pydantic import BaseModel, Field, EmailStr

Priority = Literal["low", "medium", "high", "urgent"]

class Evidence(BaseModel):
    quote: str
    start: int = 0
    end: int = 0
    source_name: str = "source"

class TaskProposal(BaseModel):
    title: str = Field(min_length=3, max_length=240)
    description: str = ""
    assignee: Optional[str] = None
    due_date: Optional[date] = None
    priority: Priority = "medium"
    dependencies: list[str] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    confidence: float = Field(default=0.65, ge=0, le=1)
    uncertainty_flags: list[str] = Field(default_factory=list)

class ExtractionResult(BaseModel):
    tasks: list[TaskProposal] = Field(default_factory=list)
    extraction_notes: list[str] = Field(default_factory=list)

class TextIngest(BaseModel):
    title: str = "Pasted meeting notes"
    text: str = Field(min_length=1, max_length=1_000_000)

class TaskPatch(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    assignee: Optional[str] = None
    due_date: Optional[date] = None
    priority: Optional[Priority] = None

class ActionDraft(BaseModel):
    channel: Literal["email", "message", "checklist"] = "email"
    recipient: Optional[str] = None
    subject: str
    body: str

# ----------------- Authentication Schemas -----------------

class UserSignUp(BaseModel):
    email: str = Field(min_length=4, max_length=120)
    password: str = Field(min_length=6, max_length=128)
    full_name: str = Field(default="", max_length=100)

class UserLogin(BaseModel):
    email: str
    password: str

class VerifyEmail(BaseModel):
    email: str
    code: str = Field(min_length=4, max_length=12)

class ResendCode(BaseModel):
    email: str

class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    contact_no: str = ""
    age: Optional[int] = None
    job_title: str = ""
    preferences: dict = Field(default_factory=dict)
    is_verified: bool
    created_at: str

class UserProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    contact_no: Optional[str] = None
    age: Optional[int] = None
    job_title: Optional[str] = None
    preferences: Optional[dict] = None

class MeetingCreate(BaseModel):
    title: str = "Voice Meeting Recording"
    transcript: str = Field(min_length=1)
    duration_seconds: int = 0
    speakers: list[str] = Field(default_factory=list)
    auto_extract_tasks: bool = True

class MeetingResponse(BaseModel):
    id: str
    title: str
    recorded_at: str
    duration_seconds: int
    transcript: str
    speakers: list[str] = Field(default_factory=list)
    task_count: int = 0
    created_at: str

class AuthResponse(BaseModel):
    token: Optional[str] = None
    user: Optional[UserResponse] = None
    requires_verification: bool = False
    message: str
    dev_code: Optional[str] = None

# ----------------- Hackathon Feature Schemas -----------------

class DispatchAction(BaseModel):
    channel: Literal["slack", "discord", "github", "calendar", "email"] = "slack"
    target: Optional[str] = None
    simulate: bool = True
    recipient: Optional[str] = None
    subject: Optional[str] = None
    body: Optional[str] = None

class ConflictResolution(BaseModel):
    resolved_due_date: str
    rationale: str = "Resolved by human review"

class DemoPresetRequest(BaseModel):
    preset_id: Literal["product_launch", "security_incident", "exec_offsite"] = "product_launch"
