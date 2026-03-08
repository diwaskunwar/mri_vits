# Predictions are now handled in scans router
# This file kept for backward compatibility - redirects to scans
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.models import User

# This router is empty - predictions are now part of Scan model
router = APIRouter()
