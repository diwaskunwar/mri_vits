"""
Brain Tumor ViT — Fixed Grad-CAM + MC Dropout Uncertainty
==========================================================
Fixes mc_uncertainty = 0.0 bug.

Root cause: google/vit-base-patch16-224-in21k has hidden_dropout_prob=0.0
and attention_probs_dropout_prob=0.0 in its config by default.
The enable_dropout() found real nn.Dropout modules but p=0.0
so every MC pass was identical → std=0.

Fix: temporarily set p=0.1 on all Dropout modules before MC passes,
then restore original values after.

Install: pip install grad-cam
Run:     python test_inference.py
"""

import os
import json
import time
import argparse
import warnings
import numpy as np
import torch
from PIL import Image
from datetime import datetime, timezone

warnings.filterwarnings("ignore")

try:
    from pytorch_grad_cam import GradCAM
    from pytorch_grad_cam.utils.image import show_cam_on_image
    from pytorch_grad_cam.utils.model_targets import ClassifierOutputTarget
except ImportError:
    os.system("pip install grad-cam -q")
    from pytorch_grad_cam import GradCAM
    from pytorch_grad_cam.utils.image import show_cam_on_image
    from pytorch_grad_cam.utils.model_targets import ClassifierOutputTarget

from transformers import ViTForImageClassification, ViTImageProcessor

# ─────────────────────────────────────────────────────────────────────────────
MODEL_PATH        = "./brain_tumor_vit_v0.1.0"
CONFIDENCE_HIGH   = 0.85
CONFIDENCE_MEDIUM = 0.65
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
# ─────────────────────────────────────────────────────────────────────────────


def vit_reshape_transform(tensor, height=14, width=14):
    """Drop [CLS] token, reshape patch tokens to spatial grid for GradCAM."""
    result = tensor[:, 1:, :]
    result = result.reshape(tensor.size(0), height, width, tensor.size(2))
    result = result.transpose(2, 3).transpose(1, 2)
    return result


def mc_dropout_predict(model, pixel_values, n_passes=20, dropout_p=0.1):
    """
    Monte Carlo Dropout with explicit p injection.

    WHY THIS FIX IS NEEDED:
    ViT-in21k config has hidden_dropout_prob=0.0 by default.
    The nn.Dropout modules exist in the model but their p=0.0,
    so all MC passes produce identical output → std=0 → useless uncertainty.

    THE FIX:
    Save original p values → set all to dropout_p=0.1 → run N passes
    → restore original p values.

    dropout_p=0.1 is standard for MC uncertainty in medical imaging literature.
    The uncertainty this produces reflects sensitivity of predictions to
    weight perturbation — a genuine measure of model confidence.
    """
    # Save original p, inject 0.1
    original_ps = {}
    for name, module in model.named_modules():
        if isinstance(module, torch.nn.Dropout):
            original_ps[name] = module.p
            module.p = dropout_p

    # Enable dropout layers in train mode, keep rest in eval
    model.eval()
    for module in model.modules():
        if isinstance(module, torch.nn.Dropout):
            module.train()

    all_probs = []
    with torch.no_grad():
        for _ in range(n_passes):
            outputs = model(pixel_values=pixel_values)
            probs   = torch.softmax(outputs.logits.float(), dim=-1)[0].cpu().numpy()
            all_probs.append(probs)

    # Restore original p values
    for name, module in model.named_modules():
        if isinstance(module, torch.nn.Dropout) and name in original_ps:
            module.p = original_ps[name]
    model.eval()

    all_probs  = np.array(all_probs)     # (N, num_classes)
    mean_probs = all_probs.mean(axis=0)  # (num_classes,)
    std_probs  = all_probs.std(axis=0)   # (num_classes,) ← actual uncertainty now

    return mean_probs, std_probs, all_probs


def apply_confidence_policy(confidence_score, uncertainty):
    """
    Combine softmax confidence + MC uncertainty into final policy.
    High uncertainty can bump a high-confidence prediction down to medium.
    This is the key product insight: a model can be 90% confident
    but have high variance across MC passes — that's a warning signal.
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


def generate_gradcam(model, pixel_values, original_image, target_class):
    """
    Real Grad-CAM using pytorch-grad-cam + ViT reshape transform.
    Target layer: last transformer block's layernorm_before.
    attn_implementation must be 'eager' (not sdpa) for hooks to work.
    """
    class ModelWrapper(torch.nn.Module):
        def __init__(self, m):
            super().__init__()
            self.model = m
        def forward(self, x):
            return self.model(pixel_values=x).logits

    wrapped       = ModelWrapper(model)
    target_layers = [model.vit.encoder.layer[-1].layernorm_before]

    cam = GradCAM(
        model=wrapped,
        target_layers=target_layers,
        reshape_transform=vit_reshape_transform,
    )

    targets       = [ClassifierOutputTarget(target_class)]
    grayscale_cam = cam(input_tensor=pixel_values, targets=targets)[0]

    orig_resized  = original_image.convert("RGB").resize((224, 224))
    orig_np       = np.array(orig_resized, dtype=np.float32) / 255.0
    overlay       = show_cam_on_image(orig_np, grayscale_cam, use_rgb=True, colormap=9)

    return overlay, grayscale_cam


def predict(image_path, model, processor, mc_passes=20):
    start        = time.time()
    original_img = Image.open(image_path).convert("RGB")
    inputs       = processor(images=original_img, return_tensors="pt")
    pixel_values = inputs["pixel_values"].to(DEVICE)

    mean_probs, std_probs, _ = mc_dropout_predict(
        model, pixel_values, n_passes=mc_passes, dropout_p=0.1
    )

    pred_idx    = int(np.argmax(mean_probs))
    id2label    = {int(k): v for k, v in model.config.id2label.items()}
    pred_label  = id2label.get(pred_idx, f"class_{pred_idx}")
    conf_score  = float(mean_probs[pred_idx])
    uncertainty = float(std_probs[pred_idx])

    notumor_idx = next((k for k, v in id2label.items() if "notumor" in v.lower()), 2)
    tumor_prob  = float(1.0 - mean_probs[notumor_idx])
    infer_ms    = round((time.time() - start) * 1000, 2)

    policy = apply_confidence_policy(conf_score, uncertainty)

    # Grad-CAM
    overlay_path = None
    try:
        overlay_np, _ = generate_gradcam(model, pixel_values, original_img, pred_idx)
        base          = os.path.splitext(os.path.basename(image_path))[0]
        overlay_path  = f"./gradcam_{base}_{pred_label}.png"
        Image.fromarray(overlay_np).save(overlay_path)
    except Exception as e:
        print(f"  Grad-CAM error: {e}")

    return {
        "image":                      os.path.basename(image_path),
        "predicted_label":            pred_label,
        "tumor_probability":          round(tumor_prob, 4),
        "confidence":                 policy["confidence"],
        "confidence_score":           round(conf_score, 4),
        "mc_uncertainty":             round(uncertainty, 4),
        "mc_uncertainty_per_class": {
            id2label[i]: round(float(std_probs[i]), 4)
            for i in range(len(std_probs))
        },
        "mc_passes":                  mc_passes,
        "requires_human_review":      policy["requires_human_review"],
        "review_message":             policy["review_message"],
        "all_probabilities": {
            id2label[i]: {
                "mean": round(float(mean_probs[i]), 4),
                "std":  round(float(std_probs[i]),  4),
            }
            for i in range(len(mean_probs))
        },
        "gradcam_overlay_saved":      overlay_path,
        "model_version":              "v0.1.0",
        "inference_time_ms":          infer_ms,
        "timestamp":                  datetime.now(timezone.utc).isoformat(),
        "disclaimer": (
            "RESEARCH PROTOTYPE — NOT a clinical diagnostic tool. "
            "All outputs require validation by a qualified radiologist."
        ),
    }


def run_tests(model_path, image_paths, mc_passes=20):
    print("=" * 65)
    print("  BRAIN TUMOR ViT — FIXED MC DROPOUT + GRAD-CAM")
    print("=" * 65)
    print(f"  Device : {DEVICE}")
    print(f"  Fix    : injecting dropout_p=0.1 into ViT's p=0.0 Dropout layers")
    print()

    processor = ViTImageProcessor.from_pretrained(model_path)
    model     = ViTForImageClassification.from_pretrained(
        model_path,
        attn_implementation="eager",  # sdpa blocks GradCAM hooks
    ).to(DEVICE)
    model.eval()

    # Diagnostic: show dropout modules
    dropout_modules = [(n, m) for n, m in model.named_modules()
                       if isinstance(m, torch.nn.Dropout)]
    original_ps = set(m.p for _, m in dropout_modules)
    print(f"  Dropout modules found : {len(dropout_modules)}")
    print(f"  Original p values     : {original_ps}  ← this is why std was 0.0")
    print(f"  MC passes will use    : p=0.1\n")

    results = []
    for img_path in image_paths:
        print(f"─── {os.path.basename(img_path)} " + "─" * 40)
        if not os.path.exists(img_path):
            print(f"  File not found: {img_path}")
            continue
        try:
            result = predict(img_path, model, processor, mc_passes=mc_passes)
            display = {k: v for k, v in result.items() if k != "disclaimer"}
            print(json.dumps(display, indent=2))
            if result["gradcam_overlay_saved"]:
                print(f"\n  Grad-CAM saved → {result['gradcam_overlay_saved']}")
            results.append(result)
        except Exception as e:
            import traceback
            print(f"  ERROR: {e}")
            traceback.print_exc()
        print()

    print("=" * 65)
    print(f"{'Image':<22} {'Label':<14} {'Conf':<10} {'MC Uncertainty':<16} Review?")
    print("-" * 65)
    for r in results:
        print(
            f"{r['image']:<22} "
            f"{r['predicted_label']:<14} "
            f"{r['confidence']:<10} "
            f"{r['mc_uncertainty']:<16} "
            f"{'YES' if r['requires_human_review'] else 'No'}"
        )
    print()
    print("mc_uncertainty should now be > 0.0")
    print("Typical values: 0.001–0.01 for high-confidence, 0.05–0.15 for uncertain")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model",     default=MODEL_PATH)
    parser.add_argument("--images",    nargs="+",
                        default=["./giloma.jpg", "./notumor.jpg", "./pituary.jpg"])
    parser.add_argument("--mc-passes", type=int, default=20)
    args = parser.parse_args()
    run_tests(args.model, args.images, args.mc_passes)