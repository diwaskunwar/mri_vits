import os
import uuid
import base64
import json
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.models import User, Scan, AuditLog
from src.schemas import ScanResponse, ScanCreate, Statistics, ScanWithPredictions
from src.auth import get_current_active_user, require_staff, require_admin
from src import model_client

router = APIRouter()

UPLOAD_DIR = "src/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.get("/scans", response_model=List[ScanResponse])
async def get_scans(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all scans - filtered by user role"""
    if current_user.role == "patient":
        scans = db.query(Scan).filter(Scan.user_id == current_user.id).order_by(Scan.created_at.desc()).offset(skip).limit(limit).all()
    else:
        scans = db.query(Scan).order_by(Scan.created_at.desc()).offset(skip).limit(limit).all()
    return scans


@router.get("/scans/{scan_id}", response_model=dict)
async def get_scan(
    scan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get scan by ID - returns stored input and gradcam images from SQLite"""
    scan = db.query(Scan).filter(Scan.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    
    # Check access
    if current_user.role == "patient" and scan.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Build response with images from blobs
    input_image = None
    gradcam_image = None
    
    if scan.image_data:
        input_image = f"data:image/jpeg;base64,{base64.b64encode(scan.image_data).decode()}"
    
    if scan.gradcam_data:
        gradcam_image = f"data:image/png;base64,{base64.b64encode(scan.gradcam_data).decode()}"
    
    return {
        "id": scan.id,
        "scan_type": scan.scan_type,
        "prediction_class": scan.prediction_class,
        "confidence": scan.confidence,
        "uncertainty": scan.uncertainty,
        "model_version": scan.model_version,
        "requires_human_review": scan.requires_human_review,
        "probabilities": scan.probabilities,
        "input_image": input_image,
        "gradcam_image": gradcam_image,
        "is_reviewed": scan.is_reviewed,
        "review_notes": scan.review_notes,
        "created_at": scan.created_at.isoformat() if scan.created_at else None,
        "status": scan.status,
        "queue_time_ms": scan.queue_time_ms,
        "process_time_ms": scan.process_time_ms,
        "patient": {
            "id": scan.user_id
        }
    }


@router.post("/predict")
async def predict_scan(
    user_id: int = Form(...),
    scan_type: str = Form("MRI"),
    notes: str = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    """Create a scan and run prediction via model service — returns gradcam + prediction"""
    # Verify patient exists
    patient = db.query(User).filter(User.id == user_id, User.role == "patient").first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
        
    # File validation: extension
    allowed_extensions = {"jpg", "jpeg", "png"}
    file_ext = file.filename.split(".")[-1].lower() if "." in file.filename else ""
    if file_ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail="Invalid file type. Only JPG, JPEG, and PNG are allowed.")
    
    # Read file content and validate size (10MB limit)
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 10MB.")
    
    # Create scan record with image as blob
    db_scan = Scan(
        scan_type=scan_type,
        image_data=content,
        notes=notes,
        user_id=user_id
    )
    db.add(db_scan)
    db.commit()
    db.refresh(db_scan)
    
    from src.task_queue import prediction_queue
    
    # Enqueue prediction task
    await prediction_queue.put((db_scan.id, content))
    
    # Log action
    log = AuditLog(
        user_id=current_user.id,
        scan_id=db_scan.id,
        action="scan_queued",
        details=json.dumps({"status": "PENDING"})
    )
    db.add(log)
    db.commit()
    
    return {
        "id": db_scan.id,
        "prediction_class": None,
        "confidence": None,
        "uncertainty": None,
        "model_version": None,
        "requires_human_review": False,
        "probabilities": None,
        "gradcam_image": None,
        "status": "PENDING",
        "created_at": db_scan.created_at.isoformat() if db_scan.created_at else None,
        "patient": {
            "id": patient.id,
            "full_name": patient.full_name,
            "username": patient.username
        }
    }



@router.post("/scans/{scan_id}/review")
async def review_scan(
    scan_id: int,
    review_notes: str = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    """Review a scan prediction"""
    scan = db.query(Scan).filter(Scan.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    
    scan.is_reviewed = True
    scan.review_notes = review_notes
    scan.reviewed_by = current_user.id
    from datetime import datetime
    scan.review_timestamp = datetime.utcnow()
    
    db.commit()
    
    # Log
    log = AuditLog(
        user_id=current_user.id,
        scan_id=scan_id,
        action="scan_reviewed",
        details=f"Scan reviewed by {current_user.username}"
    )
    db.add(log)
    db.commit()
    
    return scan


@router.delete("/scans/{scan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_scan(
    scan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Delete a scan - ADMIN ONLY"""
    scan = db.query(Scan).filter(Scan.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    
    db.delete(scan)
    db.commit()
    
    # Log action
    log = AuditLog(
        user_id=current_user.id,
        scan_id=scan_id,
        action="scan_deleted",
        details=f"Scan #{scan_id} deleted by admin {current_user.username}"
    )
    db.add(log)
    db.commit()
    
    return None


@router.get("/statistics", response_model=Statistics)
async def get_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    """Get statistics - Role-aware (Patients see only their info, Staff see global)"""
    try:
        from sqlalchemy import func, case
        
        # Determine if we should filter by patient
        filter_patient_id = None
        if current_user.role == "patient":
            filter_patient_id = current_user.id

        # 1. Start building queries
        summary_query = db.query(
            func.count(Scan.id).label("total_scans"),
            func.sum(case((Scan.status == "COMPLETED", 1), else_=0)).label("total_predictions"),
            func.sum(case(((Scan.is_reviewed == False) & (Scan.status == "COMPLETED"), 1), else_=0)).label("pending"),
            func.sum(case((Scan.is_reviewed == True, 1), else_=0)).label("reviewed"),
            func.avg(case((Scan.status == "COMPLETED", Scan.queue_time_ms))).label("avg_queue"),
            func.avg(case((Scan.status == "COMPLETED", Scan.process_time_ms))).label("avg_process")
        )

        label_query = db.query(Scan.prediction_class, func.count(Scan.id)).filter(Scan.prediction_class != None)
        recent_query = db.query(Scan)
        
        # Apply filters BEFORE limits or grouping
        if filter_patient_id:
            summary_query = summary_query.filter(Scan.user_id == filter_patient_id)
            label_query = label_query.filter(Scan.user_id == filter_patient_id)
            recent_query = recent_query.filter(Scan.user_id == filter_patient_id)
            total_patients = 1
        else:
            total_patients = db.query(User).filter(User.role == "patient").count()

        # Execute Summary
        summary = summary_query.one()

        # Execute Label Distribution
        labels_counts = label_query.group_by(Scan.prediction_class).all()
        predictions_by_label = {label: count for label, count in labels_counts}

        # Execute Recent Predictions (now apply order and limit)
        recent = recent_query.order_by(Scan.created_at.desc()).limit(5).all()

        return Statistics(
            total_patients=total_patients,
            total_scans=summary.total_scans or 0,
            total_predictions=summary.total_predictions or 0,
            predictions_pending_review=summary.pending or 0,
            predictions_reviewed=summary.reviewed or 0,
            predictions_by_label=predictions_by_label,
            recent_predictions=recent,
            avg_queue_time_ms=summary.avg_queue or 0.0,
            avg_process_time_ms=summary.avg_process or 0.0
        )
    except Exception as e:
        print(f"Stats error: {e}")
        return Statistics(
            total_patients=0,
            total_scans=0,
            total_predictions=0,
            predictions_pending_review=0,
            predictions_reviewed=0,
            predictions_by_label={},
            recent_predictions=[],
            avg_queue_time_ms=0.0,
            avg_process_time_ms=0.0
        )
