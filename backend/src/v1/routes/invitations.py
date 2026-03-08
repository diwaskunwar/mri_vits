from typing import List
import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.models import User, Invitation
from src.schemas import InvitationCreate, InvitationResponse, InvitationAccept, UserResponse
from src.auth import get_current_active_user, require_staff

router = APIRouter()

# Invitation expiry: 7 days
INVITATION_EXPIRY_DAYS = 7


@router.post("/invitations", response_model=InvitationResponse)
async def create_invitation(
    invitation_data: InvitationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    """Create an invitation token for patient/doctor (admin/doctor only)"""
    # Generate secure token
    token = secrets.token_urlsafe(32)
    
    expires_at = datetime.utcnow() + timedelta(days=INVITATION_EXPIRY_DAYS)
    
    db_invitation = Invitation(
        token=token,
        role=invitation_data.role,
        name=invitation_data.name,
        surname=invitation_data.surname,
        email=invitation_data.email,
        invited_by_user_id=current_user.id,
        expires_at=expires_at
    )
    db.add(db_invitation)
    db.commit()
    db.refresh(db_invitation)
    
    return db_invitation


@router.get("/invitations", response_model=List[InvitationResponse])
async def get_invitations(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    """Get all invitations (admin/doctor only)"""
    invitations = db.query(Invitation).order_by(Invitation.created_at.desc()).offset(skip).limit(limit).all()
    return invitations


@router.post("/invitations/accept", response_model=UserResponse)
async def accept_invitation(
    data: InvitationAccept,
    db: Session = Depends(get_db)
):
    """Accept invitation and create account"""
    # Find invitation by token
    invitation = db.query(Invitation).filter(Invitation.token == data.token).first()
    
    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid invitation token"
        )
    
    if invitation.is_used:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitation has already been used"
        )
    
    if invitation.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitation has expired"
        )
    
    # Check username doesn't exist
    existing_user = db.query(User).filter(User.username == data.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )
    
    # Create user
    from src.auth import get_password_hash
    hashed_password = get_password_hash(data.password)
    
    # Full name from invitation
    full_name = invitation.name
    if invitation.surname:
        full_name = f"{invitation.name} {invitation.surname}"
    
    new_user = User(
        username=data.username,
        email=invitation.email if invitation.email else None,
        hashed_password=hashed_password,
        full_name=full_name,
        role=invitation.role,
        is_active=True
    )
    db.add(new_user)
    
    # Mark invitation as used
    invitation.is_used = True
    invitation.used_at = datetime.utcnow()
    
    db.commit()
    db.refresh(new_user)
    
    return new_user


@router.get("/invitations/verify/{token}", response_model=InvitationResponse)
async def verify_invitation(
    token: str,
    db: Session = Depends(get_db)
):
    """Verify invitation token is valid"""
    invitation = db.query(Invitation).filter(Invitation.token == token).first()
    
    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid invitation token"
        )
    
    if invitation.is_used:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitation has already been used"
        )
    
    if invitation.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitation has expired"
        )
    
    return invitation
