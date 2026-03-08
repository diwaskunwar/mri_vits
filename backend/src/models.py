from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Float, Boolean, LargeBinary
from sqlalchemy.orm import relationship
from datetime import datetime

from src.core.database import Base


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), nullable=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100))
    role = Column(String(20), default="doctor")  # admin, doctor, patient
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships - specify foreign_keys to avoid ambiguity
    scans = relationship("Scan", back_populates="user", foreign_keys="Scan.user_id", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user", cascade="all, delete-orphan")


class Scan(Base):
    __tablename__ = "scans"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # Patient who owns the scan
    scan_type = Column(String(50))  # MRI, CT, etc.
    scan_date = Column(DateTime, default=datetime.utcnow)
    file_path = Column(String(255))
    image_data = Column(LargeBinary)
    notes = Column(Text)
    
    # Prediction results (stored directly on scan)
    prediction_class = Column(String(50))
    confidence = Column(Float)
    uncertainty = Column(Float)
    model_version = Column(String(20))
    requires_human_review = Column(Boolean, default=False)
    status = Column(String(20), default="PENDING") # PENDING, PROCESSING, COMPLETED, FAILED
    error_message = Column(Text, nullable=True)
    probabilities = Column(Text)  # JSON string
    gradcam_data = Column(LargeBinary)
    is_reviewed = Column(Boolean, default=False)
    review_notes = Column(Text)
    reviewed_by = Column(Integer, ForeignKey("users.id"))
    review_timestamp = Column(DateTime)
    
    # Queue metrics
    started_at = Column(DateTime)
    ended_at = Column(DateTime)
    queue_time_ms = Column(Float)
    process_time_ms = Column(Float)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships - specify foreign_keys to avoid ambiguity
    user = relationship("User", back_populates="scans", foreign_keys=[user_id])
    reviewer = relationship("User", foreign_keys=[reviewed_by])
    audit_logs = relationship("AuditLog", back_populates="scan")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    scan_id = Column(Integer, ForeignKey("scans.id"), nullable=True)
    action = Column(String(100), nullable=False)
    details = Column(Text)
    ip_address = Column(String(50))
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="audit_logs")
    scan = relationship("Scan", back_populates="audit_logs")


class Invitation(Base):
    __tablename__ = "invitations"
    
    id = Column(Integer, primary_key=True, index=True)
    token = Column(String(64), unique=True, index=True, nullable=False)
    role = Column(String(20), nullable=False)  # patient, doctor
    name = Column(String(100), nullable=False)
    surname = Column(String(100))
    email = Column(String(100))
    invited_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_used = Column(Boolean, default=False)
    used_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    invited_by = relationship("User")
