"""
Brain Tumor ViT — Ray Serve Inference + Load Test
==================================================
Pure Ray Serve — no FastAPI wrapper.
Ray Serve exposes its own HTTP endpoint directly.

Load test fires the real 3 test images (giloma.jpg, notumor.jpg, pituary.jpg)
concurrently — same images from test_inference.py — so results are meaningful.

How batching works:
  - Each HTTP request hits Ray Serve → queued internally
  - @serve.batch collects up to 4 requests OR waits 50ms
  - ONE GPU forward pass for the whole batch
  - batch_size_processed in response proves it's working

VRAM (ViT-base bfloat16 ~350MB per replica):
  REPLICAS=1  → 0.35GB
  REPLICAS=3  → 1.05GB  ← sweet spot for 6GB
  REPLICAS=4  → 1.40GB  ← max burst

Usage:
  pip install "ray[serve]" httpx

  python serve_inference.py              # serve only, 1 replica
  REPLICAS=3 python serve_inference.py   # 3 replicas

  # Load test with real brain scan images (runs server + test):
  python serve_inference.py --test
  REPLICAS=3 python serve_inference.py --test --rounds 5
"""

import os
import io
import time
import asyncio
import logging
import argparse
from typing import List

import numpy as np
import torch
from PIL import Image

import ray
from ray import serve
from starlette.requests import Request
from starlette.responses import JSONResponse

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("brain_tumor")

# ─────────────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────────────

MODEL_PATH   = os.getenv("MODEL_PATH",  "./brain_tumor_vit_v0.1.0")
NUM_REPLICAS = min(int(os.getenv("REPLICAS", "1")), 4)
GPU_FRACTION = round(1.0 / NUM_REPLICAS, 4)

BATCH_SIZE   = 4      # max images per GPU call
BATCH_WAIT_S = 0.05   # 50ms — flush even if batch not full

# Real test images — same as test_inference.py
TEST_IMAGES = ["./giloma.jpg", "./notumor.jpg", "./pituary.jpg"]


# ─────────────────────────────────────────────────────────────────────────────
# RAY SERVE DEPLOYMENT
# ─────────────────────────────────────────────────────────────────────────────

@serve.deployment(
    name="BrainTumorPredictor",
    num_replicas=NUM_REPLICAS,
    ray_actor_options={
        "num_gpus": GPU_FRACTION,
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
        self.model = ViTForImageClassification.from_pretrained(
            MODEL_PATH,
            torch_dtype=torch.bfloat16,
            attn_implementation="sdpa",
        ).to(self.device).eval()

        self.id2label = {int(k): v for k, v in self.model.config.id2label.items()}
        self.notumor_idx = next(
            (k for k, v in self.id2label.items() if "notumor" in v.lower()), 2
        )
        logger.info(f"[Replica] Ready — {self.id2label}")

    @serve.batch(
        max_batch_size=BATCH_SIZE,
        batch_wait_timeout_s=BATCH_WAIT_S,
    )
    async def _batch(self, batch_bytes: List[bytes]) -> List[dict]:
        """
        Ray Serve calls this with a LIST of raw image bytes.
        One GPU forward pass serves the whole batch.
        batch_size_processed in the response shows how many
        images were batched together in that single GPU call.
        """
        start = time.perf_counter()

        pil_images, errors = [], {}
        for i, raw in enumerate(batch_bytes):
            try:
                img = Image.open(io.BytesIO(raw)).convert("RGB")
                pil_images.append((i, img))
            except Exception as e:
                errors[i] = str(e)

        results = [None] * len(batch_bytes)

        for i, err in errors.items():
            results[i] = {"error": f"decode failed: {err}"}

        if pil_images:
            valid_idx  = [i for i, _ in pil_images]
            valid_imgs = [img for _, img in pil_images]

            inputs = self.processor(images=valid_imgs, return_tensors="pt")
            pv     = inputs["pixel_values"].to(self.device).to(torch.bfloat16)

            with torch.no_grad():
                logits = self.model(pixel_values=pv).logits

            probs_all = torch.softmax(logits.float(), dim=-1).cpu().numpy()
            elapsed   = round((time.perf_counter() - start) * 1000, 2)

            for pos, orig_idx in enumerate(valid_idx):
                probs      = probs_all[pos]
                pred_idx   = int(np.argmax(probs))
                pred_label = self.id2label[pred_idx]
                conf       = float(probs[pred_idx])
                tumor_prob = float(1.0 - probs[self.notumor_idx])

                band   = "high" if conf >= 0.85 else ("medium" if conf >= 0.65 else "low")
                review = conf < 0.65

                results[orig_idx] = {
                    "predicted_label":       pred_label,
                    "tumor_probability":     round(tumor_prob, 4),
                    "confidence":            band,
                    "confidence_score":      round(conf, 4),
                    "requires_human_review": review,
                    "all_probabilities": {
                        self.id2label[i]: round(float(probs[i]), 4)
                        for i in range(len(probs))
                    },
                    "model_version":         "v0.1.0",
                    "inference_time_ms":     elapsed,
                    "batch_size_processed":  len(valid_imgs),  # KEY: shows batching
                    "disclaimer":            "RESEARCH PROTOTYPE. NOT a clinical diagnostic tool.",
                }

        return results

    async def __call__(self, request: Request) -> JSONResponse:
        """
        Ray Serve HTTP handler — receives multipart or raw image bytes.
        Forwards to _batch() where it joins the batch queue.
        """
        content_type = request.headers.get("content-type", "")

        # Multipart upload (curl -F file=@image.jpg)
        if "multipart" in content_type:
            form  = await request.form()
            field = form.get("file") or next(iter(form.values()), None)
            if field is None:
                return JSONResponse({"error": "no file field in form"}, status_code=400)
            raw = await field.read()

        # Raw bytes body (direct POST)
        else:
            raw = await request.body()

        if not raw:
            return JSONResponse({"error": "empty body"}, status_code=400)

        result = await self._batch(raw)
        status = 422 if result.get("error") else 200
        return JSONResponse(result, status_code=status)


# ─────────────────────────────────────────────────────────────────────────────
# LOAD TEST — fires real brain scan images concurrently
# ─────────────────────────────────────────────────────────────────────────────

async def load_test(
    url:         str = "http://localhost:8000",
    rounds:      int = 5,
    concurrency: int = 9,   # 3 images × 3 rounds in flight = 9 concurrent
):
    """
    Fires all 3 real test images (giloma, notumor, pituary) simultaneously,
    repeated `rounds` times → `rounds × 3` total concurrent requests.

    This is the most honest load test: real images, real predictions,
    meaningful batch_size_processed values.

    Watch `batch_size_processed` in output — should show 3 or 4 when
    multiple requests land in the same 50ms window.
    """
    try:
        import httpx
    except ImportError:
        print("pip install httpx")
        return

    # Load real images from disk
    image_files = []
    for path in TEST_IMAGES:
        if not os.path.exists(path):
            print(f"  ⚠  Missing test image: {path} — skipping")
            continue
        with open(path, "rb") as f:
            image_files.append((os.path.basename(path), f.read()))

    if not image_files:
        print("  ✗  No test images found. Put giloma.jpg / notumor.jpg / pituary.jpg here.")
        return

    print(f"\n{'═'*60}")
    print(f"  LOAD TEST — real brain scan images")
    print(f"  Images      : {[f for f, _ in image_files]}")
    print(f"  Rounds      : {rounds}  (each round fires all {len(image_files)} images)")
    print(f"  Concurrency : {len(image_files) * rounds} total concurrent requests")
    print(f"  Replicas    : {NUM_REPLICAS}  |  Batch size: {BATCH_SIZE}")
    print(f"{'═'*60}\n")

    latencies   = []
    batch_sizes = []
    errors      = 0

    # Build all tasks: rounds × images
    tasks = image_files * rounds   # [(filename, bytes), ...] × rounds

    semaphore = asyncio.Semaphore(concurrency)

    async def send(client, idx, fname, raw):
        nonlocal errors
        async with semaphore:
            t0 = time.perf_counter()
            try:
                resp = await client.post(
                    url,
                    files={"file": (fname, raw, "image/jpeg")},
                    timeout=30.0,
                )
                ms = round((time.perf_counter() - t0) * 1000, 1)
                if resp.status_code == 200:
                    d  = resp.json()
                    bs = d.get("batch_size_processed", 1)
                    latencies.append(ms)
                    batch_sizes.append(bs)
                    batched_marker = "⚡ batched" if bs > 1 else "  solo"
                    print(
                        f"  [{idx:>3}] {fname:<20} "
                        f"{d['predicted_label']:<14} "
                        f"conf={d['confidence']:<8} "
                        f"batch={bs}  {ms:>6}ms  {batched_marker}"
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
            for i, (fname, raw) in enumerate(tasks)
        ])
        total_s = round(time.perf_counter() - t_wall, 2)

    # Summary
    n = len(latencies)
    if n:
        lat  = sorted(latencies)
        bavg = round(sum(batch_sizes) / len(batch_sizes), 2)
        batched_pct = round(100 * sum(1 for b in batch_sizes if b > 1) / len(batch_sizes))

        print(f"\n{'═'*60}")
        print(f"  SUMMARY")
        print(f"{'═'*60}")
        print(f"  Total requests  : {len(tasks)}")
        print(f"  Success / Error : {n} / {errors}")
        print(f"  Wall time       : {total_s}s")
        print(f"  Throughput      : {round(n / total_s, 1)} req/s")
        print(f"  Latency p50     : {lat[n // 2]}ms")
        print(f"  Latency p95     : {lat[int(n * 0.95)]}ms")
        print(f"  Latency max     : {lat[-1]}ms")
        print(f"  Avg batch size  : {bavg}  ← >1 proves batching active")
        print(f"  Batched %       : {batched_pct}%  of requests processed in a batch")
        print(f"{'═'*60}")

        if bavg > 1.3:
            print(f"\n  ✅ Dynamic batching working — {bavg}× avg batch")
            print(f"     Multiple brain scans processed per GPU call")
        else:
            print(f"\n  ⚠  Low batching — try more rounds: --rounds 10")


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Brain Tumor Ray Serve")
    parser.add_argument("--test",        action="store_true",
                        help="Start server then run load test with real images")
    parser.add_argument("--port",        type=int, default=8000)
    parser.add_argument("--rounds",      type=int, default=2,
                        help="Load test rounds (each fires all 3 images)")
    parser.add_argument("--concurrency", type=int, default=2)
    args = parser.parse_args()

    print(f"\n{'═'*60}")
    print(f"  Brain Tumor Screening — Ray Serve")
    print(f"  Replicas    : {NUM_REPLICAS}")
    print(f"  GPU/replica : {GPU_FRACTION}")
    print(f"  Batch size  : {BATCH_SIZE} images per GPU call")
    print(f"  Batch wait  : {int(BATCH_WAIT_S * 1000)}ms max queue time")
    print(f"  Port        : {args.port}")
    print(f"{'═'*60}\n")

    # Start Ray + Serve
    ray.init(num_gpus=1, ignore_reinit_error=True, logging_level=logging.WARNING)

    logger.info("Starting Ray Serve deployment …")
    serve.start(http_options={"host": "0.0.0.0", "port": args.port})
    serve.run(BrainTumorPredictor.bind(), name="brain_tumor", route_prefix="/")
    logger.info(f"Serving on http://0.0.0.0:{args.port}")

    if args.test:
        # Give replicas time to initialise (model load ~3-5s)
        logger.info("Waiting for replicas to initialise …")
        time.sleep(6)
        asyncio.run(load_test(
            url=f"http://localhost:{args.port}",
            rounds=args.rounds,
            concurrency=args.concurrency,
        ))
    else:
        # Keep serving
        print("  Server running. Ctrl+C to stop.")
        print(f"  Test endpoint: curl -X POST http://localhost:{args.port} -F file=@giloma.jpg\n")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutting down …")
            serve.shutdown()
            ray.shutdown()