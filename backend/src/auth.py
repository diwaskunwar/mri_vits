from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
import argon2
from sqlalchemy.orm import Session

from src.core.config import settings
from src.core.database import get_db
from src.models import User
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        ph = argon2.PasswordHasher()
        ph.verify(hashed_password, plain_password)
        return True
    except argon2.exceptions.VerifyMismatchError:
        return False
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    ph = argon2.PasswordHasher()
    return ph.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    return user


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


def require_admin(current_user: User = Depends(get_current_active_user)) -> User:
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current_user


def require_staff(current_user: User = Depends(get_current_active_user)) -> User:
    """Require admin, doctor, or patient role - excludes regular users"""
    if current_user.role not in ["admin", "doctor", "patient"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Staff or patient access required"
        )
    return current_user


def current_user(
    required_role: Optional[str] = None,
    required_access: Optional[str] = None,
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
) -> dict:
    """
    Validates token and returns user info dict with id, name, role and access level.
    
    Args:
        required_role: Optional role to check (e.g., "admin", "user", "radiologist")
        required_access: Optional access level to check ("read" or "write")
        db: Database session (injected by FastAPI)
        token: JWT token (injected by FastAPI)
    
    Returns:
        dict with user info: {
            "id": int,
            "username": str,
            "email": str,
            "full_name": str,
            "role": str,
            "access_level": str  # "read" or "write"
        }
    
    Raises:
        HTTPException 401 if token is invalid
        HTTPException 403 if role requirement not met
        HTTPException 403 if access level requirement not met
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    
    # Determine user access level based on role
    # admin has full read/write access
    # user and radiologist have read access (can view but not modify)
    user_access_level = "write"  # Default for admin
    if user.role == "user" or user.role == "radiologist":
        user_access_level = "read"
    
    # Check role if required
    if required_role and user.role != required_role:
        if user.role != "admin":  # Admin can access everything
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required role: {required_role}"
            )
    
    # Check access level if required
    if required_access:
        if user.role != "admin" and user_access_level != required_access:
            if required_access == "write":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Write access required. Contact admin for write permissions."
                )
    
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "access_level": user_access_level
    }
