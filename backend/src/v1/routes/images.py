"""
Image Storage API - Store and retrieve images as BLOBs in SQLite
"""

import base64
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.models import Scan, User
from src.auth import get_current_active_user

router = APIRouter()


@router.get("/scans/{scan_id}/image")
async def get_scan_image(
    scan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get scan image"""
    scan = db.query(Scan).filter(Scan.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    
    # Check access
    if current_user.role == "patient" and scan.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    if not scan.image_data:
        raise HTTPException(status_code=404, detail="Image not found")
    
    return Response(
        content=scan.image_data,
        media_type="image/jpeg",
        headers={"Content-Disposition": f"inline; filename=scan_{scan_id}.jpg"}
    )


@router.get("/scans/{scan_id}/gradcam")
async def get_gradcam_image(
    scan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get Grad-CAM image"""
    scan = db.query(Scan).filter(Scan.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    
    # Check access
    if current_user.role == "patient" and scan.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    if not scan.gradcam_data:
        raise HTTPException(status_code=404, detail="Grad-CAM not found")
    
    return Response(
        content=scan.gradcam_data,
        media_type="image/png",
        headers={"Content-Disposition": f"inline; filename=gradcam_{scan_id}.png"}
    )
