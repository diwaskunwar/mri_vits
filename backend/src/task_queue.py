import asyncio
import json
import base64
import logging
from src.core.database import SessionLocal
from src.models import Scan, AuditLog
from src import model_client
from src.v1.routes.ws import manager

logger = logging.getLogger(__name__)

# Global Task Queue
prediction_queue = asyncio.Queue()

async def process_prediction_queue():
    """Background worker that pulls scans from the queue and processes them."""
    logger.info("Prediction queue worker started.")
    while True:
        try:
            # Wait for a task
            scan_id, image_bytes = await prediction_queue.get()
            logger.info(f"Worker picked up scan_id={scan_id}")
            
            await handle_prediction(scan_id, image_bytes)
            
            # Mark task as done in the queue
            prediction_queue.task_done()
        except asyncio.CancelledError:
            logger.info("Prediction queue worker shutting down.")
            break
        except Exception as e:
            logger.error(f"Error in queue worker: {e}")

from datetime import datetime
import time

async def handle_prediction(scan_id: int, image_bytes: bytes):
    # We need a new DB session per background task
    db = SessionLocal()
    try:
        # 1. Mark as PROCESSING and notify frontend
        scan = db.query(Scan).filter(Scan.id == scan_id).first()
        if not scan:
            logger.warning(f"Scan {scan_id} not found in DB.")
            return

        scan.status = "PROCESSING"
        scan.started_at = datetime.utcnow()
        if scan.created_at:
            scan.queue_time_ms = (scan.started_at - scan.created_at).total_seconds() * 1000.0
            
        db.commit()
        await manager.send_update(scan_id, {"status": "PROCESSING"})

        # 2. Call Ray Serve Model
        logger.info(f"Sending scan {scan_id} to Ray Serve...")
        
        proc_start = time.perf_counter()
        result = await model_client.predict(image_bytes)
        proc_duration = (time.perf_counter() - proc_start) * 1000.0

        if result.get("error"):
            scan.status = "FAILED"
            scan.error_message = result.get("error")
            scan.ended_at = datetime.utcnow()
            scan.process_time_ms = proc_duration
            db.commit()
            await manager.send_update(scan_id, {"status": "FAILED", "error": scan.error_message})
            logger.error(f"Prediction failed for scan {scan_id}: {scan.error_message}")
            return

        # 3. Update DB with prediction results
        scan.prediction_class = result.get("predicted_label")
        scan.confidence = result.get("confidence_score", 0.0)
        scan.uncertainty = result.get("uncertainty")
        scan.model_version = result.get("model_version")
        scan.requires_human_review = result.get("requires_human_review", False)
        scan.probabilities = json.dumps(result.get("probabilities", {}))
        
        gradcam_b64 = result.get("gradcam_base64")
        if gradcam_b64:
            scan.gradcam_data = base64.b64decode(gradcam_b64)
            
        scan.status = "COMPLETED"
        scan.ended_at = datetime.utcnow()
        scan.process_time_ms = proc_duration
        db.commit()

        # Log action
        log = AuditLog(
            user_id=scan.user_id,
            scan_id=scan.id,
            action="async_prediction_completed",
            details=json.dumps({
                "prediction": scan.prediction_class,
                "confidence": scan.confidence,
            })
        )
        db.add(log)
        db.commit()

        # 4. Notify frontend of completion
        payload = {
            "status": "COMPLETED",
            "prediction_class": scan.prediction_class,
            "confidence": scan.confidence,
            "uncertainty": scan.uncertainty,
            "requires_human_review": scan.requires_human_review,
            "probabilities": scan.probabilities,
            "queue_time_ms": scan.queue_time_ms,
            "process_time_ms": scan.process_time_ms,
            "gradcam_image": f"data:image/png;base64,{gradcam_b64}" if gradcam_b64 else None
        }
        await manager.send_update(scan_id, payload)
        logger.info(f"Scan {scan_id} processing completed successfully in {proc_duration:.0f}ms.")

    except Exception as e:
        logger.error(f"Unexpected error processing scan {scan_id}: {e}")
        scan.status = "FAILED"
        scan.error_message = str(e)
        db.commit()
        await manager.send_update(scan_id, {"status": "FAILED", "error": str(e)})
    finally:
        db.close()
