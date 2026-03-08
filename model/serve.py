"""
Brain Tumor ViT — Ray Serve Inference Service
==============================================
Full-featured Ray Serve deployment:
  • Batch inference via @serve.batch for GPU efficiency
  • MC Dropout (20 passes) for uncertainty estimation
  • Grad-CAM heatmap visualization
  • Confidence policy (high/medium/low) with human review flag
  • Health check endpoint

This is the MODEL SERVICE — the backend calls this over HTTP.

Usage:
  # Start with 1 replica (default)
  uv run python serve.py

  # Start with multiple replicas (for multi-GPU or fractional GPU)
  REPLICAS=3 uv run python serve.py

  # Custom port
  uv run python serve.py --port 8001

  # Load test with real images
  uv run python serve.py --test --rounds 5
"""

import os
import io
import time
import base64
import asyncio
import logging
import argparse
from typing import List, Dict, Any
from datetime import datetime, timezone

import numpy as np
import torch
import torch.nn as nn
from PIL import Image

import ray
from ray import serve
from starlette.requests import Request
from starlette.responses import JSONResponse

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("brain_tumor_serve")

# ─────────────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────────────

MODEL_PATH   = os.getenv("MODEL_PATH", "diwaskunwar10/brain-tumor-vit-candor")
NUM_REPLICAS = min(int(os.getenv("REPLICAS", "1")), 4)
GPU_FRACTION = round(1.0 / max(NUM_REPLICAS, 1), 4)

BATCH_SIZE    = 4       # max images per GPU call
BATCH_WAIT_S  = 0.05    # 50ms — flush even if batch not full
MC_PASSES     = 20      # Monte Carlo Dropout passes
MC_DROPOUT_P  = 0.1     # Dropout probability for MC passes

# Confidence thresholds
CONFIDENCE_HIGH   = 0.85
CONFIDENCE_MEDIUM = 0.65

# Real test images for load testing
TEST_IMAGES = ["./giloma.jpg", "./notumor.jpg", "./pituary.jpg"]


# ─────────────────────────────────────────────────────────────────────────────
# HELPER FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

def vit_reshape_transform(tensor, height=14, width=14):
    """Drop [CLS] token, reshape patch tokens to spatial grid for GradCAM."""
    result = tensor[:, 1:, :]
    result = result.reshape(tensor.size(0), height, width, tensor.size(2))
    result = result.transpose(2, 3).transpose(1, 2)
    return result


def mc_dropout_predict(model, pixel_values, n_passes=10, dropout_p=0.1):
    """
    Monte Carlo Dropout with batched passes for speed.
    """
    original_ps = {}
    for name, module in model.named_modules():
        if isinstance(module, nn.Dropout):
            original_ps[name] = module.p
            module.p = dropout_p

    model.eval()
    for module in model.modules():
        if isinstance(module, nn.Dropout):
            module.train()

    # Move to device
    pixel_values = pixel_values.to(next(model.parameters()).device)
    
    # Repeat image for batched inference
    # Shape: [batch_size, 3, 224, 224] -> [n_passes * batch_size, 3, 224, 224]
    batch_size = pixel_values.shape[0]
    pixel_values_batched = pixel_values.repeat(n_passes, 1, 1, 1)

    with torch.no_grad():
        outputs = model(pixel_values=pixel_values_batched)
        logits = outputs.logits.float()
        all_probs = torch.softmax(logits, dim=-1).cpu().numpy()

    # Restore original p values
    for name, module in model.named_modules():
        if isinstance(module, nn.Dropout) and name in original_ps:
            module.p = original_ps[name]
    model.eval()

    # Reshape back to [n_passes, batch_size, num_classes]
    all_probs = all_probs.reshape(n_passes, batch_size, -1)
    
    # We only care about the first image in the batch since we are in single-predict context
    # or we handle all images if we want to. But model_service usually gets 1 image per request.
    mean_probs = all_probs.mean(axis=0)[0]
    std_probs = all_probs.std(axis=0)[0]

    return mean_probs, std_probs


def apply_confidence_policy(confidence_score: float, uncertainty: float) -> dict:
    """
    Combine softmax confidence + MC uncertainty into final policy.
    High uncertainty bumps down the confidence band.
    """
    if confidence_score >= CONFIDENCE_HIGH and uncertainty < 0.05:
        return {
            "confidence": "high",
            "requires_human_review": False,
            "review_message": None,
        }
    elif confidence_score >= CONFIDENCE_MEDIUM and uncertainty < 0.12:
        return {
            "confidence": "medium",
            "requires_human_review": False,
            "review_message": "Moderate confidence — radiologist review recommended.",
        }
    else:
        return {
            "confidence": "low",
            "requires_human_review": True,
            "review_message": (
                "Low confidence or high MC uncertainty — "
                "requires radiologist review before any clinical action. "
                "DO NOT use as diagnostic basis."
            ),
        }


def generate_gradcam(cam, pixel_values, original_image, target_class):
    """
    Grad-CAM using pytorch-grad-cam + ViT reshape transform.
    """
    from pytorch_grad_cam.utils.image import show_cam_on_image
    from pytorch_grad_cam.utils.model_targets import ClassifierOutputTarget

    targets = [ClassifierOutputTarget(target_class)]
    grayscale_cam = cam(input_tensor=pixel_values, targets=targets)[0]

    orig_resized = original_image.convert("RGB").resize((224, 224))
    orig_np = np.array(orig_resized, dtype=np.float32) / 255.0
    overlay = show_cam_on_image(orig_np, grayscale_cam, use_rgb=True, colormap=9)

    return overlay


# ─────────────────────────────────────────────────────────────────────────────
# RAY SERVE DEPLOYMENT
# ─────────────────────────────────────────────────────────────────────────────

@serve.deployment(
    name="BrainTumorPredictor",
    num_replicas=NUM_REPLICAS,
    ray_actor_options={
        "num_gpus": GPU_FRACTION if torch.cuda.is_available() else 0,
        "num_cpus": 1,
    },
    max_ongoing_requests=32,
)
class BrainTumorPredictor:

    def __init__(self):
        from transformers import ViTForImageClassification, ViTImageProcessor

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logger.info(f"[Replica] device={self.device}  gpu_fraction={GPU_FRACTION}")

        self.processor = ViTImageProcessor.from_pretrained(MODEL_PATH)

        # Use eager attn for Grad-CAM hooks (sdpa blocks hooks)
        self.model = ViTForImageClassification.from_pretrained(
            MODEL_PATH,
            attn_implementation="eager",
        ).to(self.device).eval()

        self.id2label = {int(k): v for k, v in self.model.config.id2label.items()}
        self.labels = [self.id2label[i] for i in range(len(self.id2label))]
        self.notumor_idx = next(
            (k for k, v in self.id2label.items() if "notumor" in v.lower()), 2
        )

        # Initialize GradCAM singleton for this replica
        from pytorch_grad_cam import GradCAM
        class ModelWrapper(nn.Module):
            def __init__(self, m):
                super().__init__()
                self.model = m
            def forward(self, x):
                return self.model(pixel_values=x).logits

        wrapped = ModelWrapper(self.model)
        target_layers = [self.model.vit.encoder.layer[-1].layernorm_before]
        self.cam = GradCAM(
            model=wrapped,
            target_layers=target_layers,
            reshape_transform=vit_reshape_transform,
        )

        # Load model metadata for version
        self.model_version = "v0.1.0"
        try:
            import json
            meta_path = os.path.join(MODEL_PATH, "model_metadata.json")
            if os.path.exists(meta_path):
                with open(meta_path) as f:
                    meta = json.load(f)
                    self.model_version = meta.get("model_version", "v0.1.0")
        except Exception:
            pass

        logger.info(f"[Replica] Ready — {self.id2label} — version {self.model_version}")

    def _predict_single(self, image_bytes: bytes) -> dict:
        """Full prediction for a single image: MC Dropout + Grad-CAM."""
        start = time.perf_counter()

        try:
            pil_image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        except Exception as e:
            return {"error": f"Image decode failed: {e}"}

        inputs = self.processor(images=pil_image, return_tensors="pt")
        pixel_values = inputs["pixel_values"].to(self.device)

        # MC Dropout for uncertainty
        mean_probs, std_probs = mc_dropout_predict(
            self.model, pixel_values, n_passes=MC_PASSES, dropout_p=MC_DROPOUT_P
        )

        pred_idx = int(np.argmax(mean_probs))
        pred_label = self.id2label[pred_idx]
        conf_score = float(mean_probs[pred_idx])
        uncertainty = float(std_probs[pred_idx])
        tumor_prob = float(1.0 - mean_probs[self.notumor_idx])

        # Confidence policy
        policy = apply_confidence_policy(conf_score, uncertainty)

        # Grad-CAM
        gradcam_b64 = None
        try:
            overlay_np = generate_gradcam(
                self.cam, pixel_values, pil_image, pred_idx
            )
            from io import BytesIO
            buf = BytesIO()
            Image.fromarray(overlay_np).save(buf, format="PNG")
            gradcam_b64 = base64.b64encode(buf.getvalue()).decode()
        except Exception as e:
            logger.warning(f"Grad-CAM failed: {e}")

        elapsed = round((time.perf_counter() - start) * 1000, 2)

        return {
            "predicted_label": pred_label,
            "confidence_score": round(conf_score, 4),
            "confidence": policy["confidence"],
            "uncertainty": round(uncertainty, 4),
            "tumor_probability": round(tumor_prob, 4),
            "requires_human_review": policy["requires_human_review"],
            "review_message": policy["review_message"],
            "probabilities": {
                self.labels[i]: round(float(mean_probs[i]), 4)
                for i in range(len(mean_probs))
            },
            "gradcam_base64": gradcam_b64,
            "model_version": self.model_version,
            "inference_time_ms": elapsed,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "disclaimer": "RESEARCH PROTOTYPE. NOT a clinical diagnostic tool.",
        }

    @serve.batch(
        max_batch_size=BATCH_SIZE,
        batch_wait_timeout_s=BATCH_WAIT_S,
    )
    async def _batch_predict(self, batch_bytes: List[bytes]) -> List[dict]:
        """
        Batch handler — Ray Serve collects requests and calls this.
        Each image gets full MC Dropout + Grad-CAM processing.
        """
        results = []
        for image_bytes in batch_bytes:
            result = self._predict_single(image_bytes)
            result["batch_size_processed"] = len(batch_bytes)
            results.append(result)
        return results

    async def __call__(self, request: Request) -> JSONResponse:
        """HTTP handler — accepts multipart or raw image bytes."""
        content_type = request.headers.get("content-type", "")

        if "multipart" in content_type:
            form = await request.form()
            field = form.get("file") or next(iter(form.values()), None)
            if field is None:
                return JSONResponse({"error": "no file field in form"}, status_code=400)
            raw = await field.read()
        else:
            raw = await request.body()

        if not raw:
            return JSONResponse({"error": "empty body"}, status_code=400)

        result = await self._batch_predict(raw)
        status = 422 if result.get("error") else 200
        return JSONResponse(result, status_code=status)


# ─────────────────────────────────────────────────────────────────────────────
# HEALTH CHECK APP (mounted alongside the deployment)
# ─────────────────────────────────────────────────────────────────────────────

@serve.deployment(num_replicas=1)
class HealthCheck:
    async def __call__(self, request: Request) -> JSONResponse:
        return JSONResponse({
            "status": "healthy",
            "service": "brain-tumor-model",
            "model_path": MODEL_PATH,
            "replicas": NUM_REPLICAS,
            "gpu_available": torch.cuda.is_available(),
        })


# ─────────────────────────────────────────────────────────────────────────────
# LOAD TEST
# ─────────────────────────────────────────────────────────────────────────────

async def load_test(
    url: str = "http://localhost:8001",
    rounds: int = 3,
    concurrency: int = 9,
):
    """Fire all test images concurrently to verify batching and correctness."""
    try:
        import httpx
    except ImportError:
        print("pip install httpx")
        return

    image_files = []
    for path in TEST_IMAGES:
        if not os.path.exists(path):
            print(f"  ⚠  Missing: {path} — skipping")
            continue
        with open(path, "rb") as f:
            image_files.append((os.path.basename(path), f.read()))

    if not image_files:
        print("  ✗  No test images found.")
        return

    print(f"\n{'═'*60}")
    print(f"  LOAD TEST — real brain scan images")
    print(f"  Images      : {[f for f, _ in image_files]}")
    print(f"  Rounds      : {rounds}")
    print(f"  Replicas    : {NUM_REPLICAS}")
    print(f"{'═'*60}\n")

    latencies = []
    errors = 0
    tasks_data = image_files * rounds
    semaphore = asyncio.Semaphore(concurrency)

    async def send(client, idx, fname, raw):
        nonlocal errors
        async with semaphore:
            t0 = time.perf_counter()
            try:
                resp = await client.post(
                    f"{url}/predict",
                    files={"file": (fname, raw, "image/jpeg")},
                    timeout=60.0,
                )
                ms = round((time.perf_counter() - t0) * 1000, 1)
                if resp.status_code == 200:
                    d = resp.json()
                    latencies.append(ms)
                    print(
                        f"  [{idx:>3}] {fname:<20} "
                        f"{d['predicted_label']:<14} "
                        f"conf={d['confidence']:<8} "
                        f"unc={d.get('uncertainty', 'N/A'):<8} "
                        f"{ms:>7}ms"
                    )
                else:
                    errors += 1
                    print(f"  [{idx:>3}] {fname:<20} ❌ HTTP {resp.status_code}")
            except Exception as e:
                errors += 1
                print(f"  [{idx:>3}] {fname:<20} ❌ {e}")

    async with httpx.AsyncClient() as client:
        t_wall = time.perf_counter()
        await asyncio.gather(*[
            send(client, i, fname, raw)
            for i, (fname, raw) in enumerate(tasks_data)
        ])
        total_s = round(time.perf_counter() - t_wall, 2)

    n = len(latencies)
    if n:
        lat = sorted(latencies)
        print(f"\n{'═'*60}")
        print(f"  SUMMARY")
        print(f"  Success / Error : {n} / {errors}")
        print(f"  Wall time       : {total_s}s")
        print(f"  Throughput      : {round(n / total_s, 1)} req/s")
        print(f"  Latency p50     : {lat[n // 2]}ms")
        print(f"  Latency p95     : {lat[int(n * 0.95)]}ms")
        print(f"{'═'*60}")


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Brain Tumor Ray Serve")
    parser.add_argument("--test", action="store_true", help="Run load test after start")
    parser.add_argument("--port", type=int, default=8001)
    parser.add_argument("--rounds", type=int, default=2)
    parser.add_argument("--concurrency", type=int, default=6)
    args = parser.parse_args()

    print(f"\n{'═'*60}")
    print(f"  Brain Tumor Model Service — Ray Serve")
    print(f"  Model     : {MODEL_PATH}")
    print(f"  Replicas  : {NUM_REPLICAS}")
    print(f"  GPU frac  : {GPU_FRACTION}")
    print(f"  Batch     : {BATCH_SIZE} images / {int(BATCH_WAIT_S * 1000)}ms wait")
    print(f"  MC passes : {MC_PASSES}")
    print(f"  Port      : {args.port}")
    print(f"{'═'*60}\n")

    # Start Ray
    ray.init(
        num_gpus=1 if torch.cuda.is_available() else 0,
        ignore_reinit_error=True,
        logging_level=logging.WARNING,
    )

    # Deploy
    logger.info("Starting Ray Serve …")
    serve.start(http_options={"host": "0.0.0.0", "port": args.port})

    # Mount predictor on /predict, health on /health
    serve.run(BrainTumorPredictor.bind(), name="brain_tumor", route_prefix="/predict")
    serve.run(HealthCheck.bind(), name="health", route_prefix="/health")

    logger.info(f"Serving on http://0.0.0.0:{args.port}")
    logger.info(f"  POST http://0.0.0.0:{args.port}/predict  — inference")
    logger.info(f"  GET  http://0.0.0.0:{args.port}/health   — health check")

    if args.test:
        logger.info("Waiting for replicas to initialise …")
        time.sleep(8)
        asyncio.run(load_test(
            url=f"http://localhost:{args.port}",
            rounds=args.rounds,
            concurrency=args.concurrency,
        ))
    else:
        print(f"\n  Server running. Ctrl+C to stop.")
        print(f"  Test: curl -X POST http://localhost:{args.port}/predict -F file=@giloma.jpg\n")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutting down …")
            serve.shutdown()
            ray.shutdown()
