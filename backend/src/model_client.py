"""
Model Service Client
====================
HTTP client that sends images to the Ray Serve model service for prediction.
Falls back gracefully when the model service is unavailable.
"""

import httpx
import logging
from typing import Optional
from src.core.config import settings

logger = logging.getLogger("model_client")


async def predict(image_bytes: bytes, timeout: float = 120.0) -> dict:
    """
    Send image bytes to the model service and return prediction results.
    
    Returns dict with keys:
        predicted_label, confidence_score, confidence, uncertainty,
        tumor_probability, requires_human_review, review_message,
        probabilities, gradcam_base64, model_version, inference_time_ms,
        timestamp, disclaimer
    """
    url = f"{settings.MODEL_SERVICE_URL}/predict"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                files={"file": ("scan.jpg", image_bytes, "image/jpeg")},
                timeout=timeout,
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Model service returned {response.status_code}: {response.text}")
                return {
                    "error": f"Model service error: HTTP {response.status_code}",
                    "predicted_label": "error",
                    "confidence_score": 0.0,
                    "confidence": "low",
                    "uncertainty": 1.0,
                    "requires_human_review": True,
                    "review_message": f"Model service returned HTTP {response.status_code}",
                    "probabilities": {},
                    "gradcam_base64": None,
                    "model_version": "unknown",
                }
    except httpx.ConnectError:
        logger.error(f"Cannot connect to model service at {url}")
        return {
            "error": "Model service unavailable",
            "predicted_label": "service_unavailable",
            "confidence_score": 0.0,
            "confidence": "low",
            "uncertainty": 1.0,
            "requires_human_review": True,
            "review_message": "Model service is not running. Please start the model service.",
            "probabilities": {},
            "gradcam_base64": None,
            "model_version": "unknown",
        }
    except httpx.TimeoutException:
        logger.error(f"Model service timed out after {timeout}s")
        return {
            "error": "Model service timeout",
            "predicted_label": "timeout",
            "confidence_score": 0.0,
            "confidence": "low",
            "uncertainty": 1.0,
            "requires_human_review": True,
            "review_message": "Model inference timed out. The image may be too large or the service is overloaded.",
            "probabilities": {},
            "gradcam_base64": None,
            "model_version": "unknown",
        }
    except Exception as e:
        logger.error(f"Model service error: {e}")
        return {
            "error": str(e),
            "predicted_label": "error",
            "confidence_score": 0.0,
            "confidence": "low",
            "uncertainty": 1.0,
            "requires_human_review": True,
            "review_message": f"Unexpected error: {e}",
            "probabilities": {},
            "gradcam_base64": None,
            "model_version": "unknown",
        }


async def health_check() -> dict:
    """Check if the model service is healthy."""
    url = f"{settings.MODEL_SERVICE_URL}/health"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=5.0)
            if response.status_code == 200:
                return response.json()
    except Exception:
        pass
    return {"status": "unavailable"}
