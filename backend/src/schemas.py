from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional, List
from datetime import datetime


# User schemas
class UserBase(BaseModel):
    username: str
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    role: str = "doctor"

    @field_validator("email", "full_name", mode="before")
    @classmethod
    def empty_string_to_none(cls, v):
        if v == "":
            return None
        return v


class UserCreate(UserBase):
    password: str


class UserResponse(UserBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class PatientResponse(UserResponse):
    total_scans: int = 0
    last_scan_at: Optional[datetime] = None


# Scan schemas
class ScanBase(BaseModel):
    scan_type: Optional[str] = "MRI"
    notes: Optional[str] = None


class ScanCreate(ScanBase):
    user_id: int  # Patient who owns the scan


class ScanResponse(ScanBase):
    id: int
    user_id: int
    scan_date: Optional[datetime]
    file_path: Optional[str]
    notes: Optional[str]
    prediction_class: Optional[str]
    confidence: Optional[float]
    uncertainty: Optional[float] = None
    model_version: Optional[str] = None
    requires_human_review: Optional[bool] = False
    probabilities: Optional[str]
    is_reviewed: bool
    review_notes: Optional[str]
    reviewed_by: Optional[int]
    review_timestamp: Optional[datetime]
    created_at: datetime
    user: Optional[UserResponse] = None
    status: str
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    queue_time_ms: Optional[float] = None
    process_time_ms: Optional[float] = None

    class Config:
        from_attributes = True


class ScanWithPredictions(ScanResponse):
    gradcam_image: Optional[str] = None
    input_image: Optional[str] = None

# Invitation schemas
class InvitationBase(BaseModel):
    role: str = "patient"
    name: str
    surname: Optional[str] = None
    email: Optional[EmailStr] = None

    @field_validator("email", "surname", mode="before")
    @classmethod
    def empty_string_to_none(cls, v):
        if v == "":
            return None
        return v


class InvitationCreate(InvitationBase):
    pass


class InvitationAccept(BaseModel):
    token: str
    username: str
    password: str


class InvitationResponse(InvitationBase):
    id: int
    token: str
    invited_by_user_id: int
    is_used: bool
    used_at: Optional[datetime]
    expires_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True


# Audit log schemas
class AuditLogResponse(BaseModel):
    id: int
    user_id: Optional[int]
    scan_id: Optional[int]
    action: str
    details: Optional[str]
    ip_address: Optional[str]
    timestamp: datetime
    user: Optional[UserResponse] = None

    class Config:
        from_attributes = True


# Statistics schema
class Statistics(BaseModel):
    total_patients: int = 0
    total_scans: int = 0
    total_predictions: int = 0
    predictions_pending_review: int = 0
    predictions_reviewed: int = 0
    predictions_by_label: dict = {}
    recent_predictions: List[ScanResponse] = []
    avg_queue_time_ms: float = 0.0
    avg_process_time_ms: float = 0.0


# Auth schemas
class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


class LoginRequest(BaseModel):
    username: str
    password: str
