from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import func

from src.core.database import get_db
from src.models import User, Scan
from src.schemas import UserCreate, UserResponse, PatientResponse
from src.auth import get_current_active_user, create_access_token, get_password_hash, verify_password
from src.auth import get_current_active_user, require_staff, require_admin

router = APIRouter()


def hash_password(password: str) -> str:
    return get_password_hash(password)


def check_password(plain_password: str, hashed_password: str) -> bool:
    return verify_password(plain_password, hashed_password)


@router.post("/token")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Login endpoint"""
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not check_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/auth/login")
async def auth_login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Login endpoint - returns token and user info"""
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not check_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    
    access_token = create_access_token(data={"sub": user.username})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "is_active": user.is_active
        }
    }


@router.get("/auth/validate")
async def auth_validate(
    current_user: User = Depends(get_current_active_user)
):
    """Validate token and return user info"""
    return {
        "valid": True,
        "user": {
            "id": current_user.id,
            "username": current_user.username,
            "email": current_user.email,
            "full_name": current_user.full_name,
            "role": current_user.role,
            "is_active": current_user.is_active
        }
    }


@router.post("/register", response_model=UserResponse)
async def register(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    """Register a new user"""
    existing_user = db.query(User).filter(User.username == user_data.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    existing_email = db.query(User).filter(User.email == user_data.email).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    hashed_password = hash_password(user_data.password)
    db_user = User(
        username=user_data.username,
        email=user_data.email,
        full_name=user_data.full_name,
        role=user_data.role,
        hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    """Get current user info"""
    return current_user


@router.get("/users", response_model=list[UserResponse])
async def get_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all users (admin/doctor only)"""
    if current_user.role not in ["admin", "doctor"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    users = db.query(User).offset(skip).limit(limit).all()
    return users


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Delete a user - ADMIN ONLY"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Don't let users delete themselves
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
        
    db.delete(user)
    db.commit()
    
    return None


@router.get("/patients", response_model=list[PatientResponse])
async def get_patients(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all patients with scan metadata (admin/doctor only)"""
    if current_user.role not in ["admin", "doctor"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Efficiently join with scans to get counts and last scan date
    patients_query = (
        db.query(
            User,
            func.count(Scan.id).label("total_scans"),
            func.max(Scan.created_at).label("last_scan_at")
        )
        .filter(User.role == "patient")
        .outerjoin(Scan, User.id == Scan.user_id)
        .group_by(User.id)
        .offset(skip)
        .limit(limit)
    )
    
    results = patients_query.all()
    
    output = []
    for user, total_scans, last_scan_at in results:
        # Create PatientResponse from User and additional fields
        p_dict = {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "is_active": user.is_active,
            "created_at": user.created_at,
            "total_scans": total_scans,
            "last_scan_at": last_scan_at
        }
        output.append(p_dict)
        
    return output
