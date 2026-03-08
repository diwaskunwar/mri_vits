from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.models import User, AuditLog
from src.schemas import AuditLogResponse
from src.auth import get_current_active_user, require_staff

router = APIRouter()


@router.get("/audit-logs", response_model=List[AuditLogResponse])
async def get_audit_logs(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    """Get audit logs (admin/doctor only)"""
    logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).offset(skip).limit(limit).all()
    return logs
