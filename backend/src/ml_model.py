import os
from typing import Dict, Any, Optional, List
import numpy as np
import torch
import torch.nn as nn
from PIL import Image
from datetime import datetime, timezone
from pytorch_grad_cam import GradCAM
from pytorch_grad_cam.utils.image import show_cam_on_image
from pytorch_grad_cam.utils.model_targets import ClassifierOutputTarget

from src.core.config import settings


# Constants from the working implementation
CONFIDENCE_HIGH = 0.85
CONFIDENCE_MEDIUM = 0.65
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")


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
        if isinstance(module, nn.Dropout):
            original_ps[name] = module.p
            module.p = dropout_p

    # Enable dropout layers in train mode, keep rest in eval
    model.eval()
    for module in model.modules():
        if isinstance(module, nn.Dropout):
            module.train()

    # Move input to the same device as the model
    pixel_values = pixel_values.to(next(model.parameters()).device)
    
    all_probs = []
    with torch.no_grad():
        for _ in range(n_passes):
            outputs = model(pixel_values=pixel_values)
            probs = torch.softmax(outputs.logits.float(), dim=-1)[0].cpu().numpy()
            all_probs.append(probs)

    # Restore original p values
    for name, module in model.named_modules():
        if isinstance(module, nn.Dropout) and name in original_ps:
            module.p = original_ps[name]
    model.eval()

    all_probs = np.array(all_probs)     # (N, num_classes)
    mean_probs = all_probs.mean(axis=0)  # (num_classes,)
    std_probs = all_probs.std(axis=0)    # (num_classes,) ← actual uncertainty now

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

    class ModelWrapper(nn.Module):
        def __init__(self, m):
            super().__init__()
            self.model = m
        def forward(self, x):
            return self.model(pixel_values=x).logits

    wrapped = ModelWrapper(model)
    target_layers = [model.vit.encoder.layer[-1].layernorm_before]

    cam = GradCAM(
        model=wrapped,
        target_layers=target_layers,
        reshape_transform=vit_reshape_transform,
    )

    targets = [ClassifierOutputTarget(target_class)]
    grayscale_cam = cam(input_tensor=pixel_values, targets=targets)[0]

    orig_resized = original_image.convert("RGB").resize((224, 224))
    orig_np = np.array(orig_resized, dtype=np.float32) / 255.0
    overlay = show_cam_on_image(orig_np, grayscale_cam, use_rgb=True, colormap=9)

    return overlay, grayscale_cam


class ModelLoader:
    def __init__(self):
        self.model = None
        self.processor = None
        self.labels = ["glioma", "meningioma", "notumor", "pituitary"]
        self.loaded = False
        # Temperature scaling for confidence calibration
        self.temperature = 1.0  # Default temperature (1.0 = no calibration)
        self.mc_passes = 20  # Number of MC Dropout passes for uncertainty estimation
    
    def load_model(self):
        """Load the ML model for inference"""
        model_path = settings.MODEL_PATH
        
        if not os.path.exists(model_path):
            print(f"Model path does not exist: {model_path}")
            self.loaded = False
            return
        
        try:
            from transformers import ViTForImageClassification, ViTImageProcessor
            
            print(f"Loading model from {model_path}...")
            self.processor = ViTImageProcessor.from_pretrained(model_path)
            self.model = ViTForImageClassification.from_pretrained(
                model_path,
                attn_implementation="eager"  # sdpa blocks GradCAM hooks
            ).to(DEVICE)  # Move model to device
            self.model.eval()
            
            self.loaded = True
            print("Model loaded successfully!")
            print(f"  Device: {DEVICE}")
            
            # Diagnostic: show dropout modules
            dropout_modules = [(n, m) for n, m in self.model.named_modules() 
                             if isinstance(m, torch.nn.Dropout)]
            original_ps = set(m.p for _, m in dropout_modules)
            print(f"  Dropout modules found: {len(dropout_modules)}")
            print(f"  Original p values: {original_ps}")
            print(f"  MC passes will use: p=0.1")
            
        except Exception as e:
            print(f"Error loading model: {e}")
            import traceback
            traceback.print_exc()
            self.loaded = False
    
    def is_loaded(self) -> bool:
        return self.loaded
    
    def set_temperature(self, temperature: float):
        """Set temperature for confidence calibration (1.0 = no calibration)"""
        self.temperature = max(0.1, temperature)
    
    def set_mc_passes(self, passes: int):
        """Set number of MC Dropout passes for uncertainty estimation"""
        self.mc_passes = max(1, passes)
    
    def _apply_temperature_scaling(self, logits: torch.Tensor) -> torch.Tensor:
        """Apply temperature scaling to logits before softmax"""
        return logits / self.temperature
    
    def predict(self, image_path: str) -> Dict[str, Any]:
        """Run prediction on an image with optional temperature scaling"""
        if not self.loaded:
            return {
                "prediction_class": "model_not_loaded",
                "confidence": 0.0,
                "probabilities": {}
            }
        
        try:
            # Load and preprocess image
            image = Image.open(image_path).convert("RGB")
            
            # Run inference
            inputs = self.processor(images=image, return_tensors="pt")
            pixel_values = inputs["pixel_values"].to(DEVICE)
            
            with torch.no_grad():
                outputs = self.model(pixel_values=pixel_values)
            
            # Apply temperature scaling before softmax
            scaled_logits = self._apply_temperature_scaling(outputs.logits)
            probs = torch.nn.functional.softmax(scaled_logits, dim=-1)
            probs_list = probs[0].tolist()
            
            # Get prediction
            predicted_class_idx = probs[0].argmax().item()
            predicted_class = self.labels[predicted_class_idx]
            confidence = probs[0][predicted_class_idx].item()
            
            # Create probabilities dict
            probabilities = {
                self.labels[i]: probs_list[i] 
                for i in range(len(self.labels))
            }
            
            return {
                "prediction_class": predicted_class,
                "confidence": confidence,
                "probabilities": probabilities,
                "temperature": self.temperature
            }
            
        except Exception as e:
            print(f"Error during prediction: {e}")
            return {
                "prediction_class": "error",
                "confidence": 0.0,
                "probabilities": {"error": str(e)}
            }
    
    def predict_with_gradcam(self, image_path: str) -> Dict[str, Any]:
        """
        Run prediction with Grad-CAM heatmap visualization using MC Dropout for uncertainty.
        Returns prediction + base64-encoded heatmap + uncertainty estimates.
        Based on the working implementation from test_gradcam.py.
        """
        if not self.loaded:
            return {
                "prediction_class": "model_not_loaded",
                "confidence": 0.0,
                "probabilities": {},
                "gradcam_image": None,
                "mc_uncertainty": None,
                "requires_human_review": True,
                "review_message": "Model not loaded"
            }
        
        try:
            import cv2
            import base64
            from io import BytesIO
            
            # Load and preprocess image
            original_image = Image.open(image_path).convert("RGB")
            inputs = self.processor(images=original_image, return_tensors="pt")
            pixel_values = inputs["pixel_values"].to(DEVICE)
            
            # Run MC Dropout prediction for uncertainty estimation
            mean_probs, std_probs, _ = mc_dropout_predict(
                self.model, pixel_values, n_passes=self.mc_passes, dropout_p=0.1
            )
            
            # Get prediction
            pred_idx = int(np.argmax(mean_probs))
            id2label = {i: label for i, label in enumerate(self.labels)}
            pred_label = id2label.get(pred_idx, f"class_{pred_idx}")
            conf_score = float(mean_probs[pred_idx])
            uncertainty = float(std_probs[pred_idx])
            
            # Calculate tumor probability
            notumor_idx = next((i for i, v in id2label.items() if "notumor" in v.lower()), 2)
            tumor_prob = float(1.0 - mean_probs[notumor_idx])
            
            # Apply confidence policy
            policy = apply_confidence_policy(conf_score, uncertainty)
            
            # Generate Grad-CAM
            gradcam_b64 = None
            overlay_path = None
            try:
                overlay_np, _ = generate_gradcam(
                    self.model, pixel_values, original_image, pred_idx
                )
                
                # Save overlay to buffer
                buffered = BytesIO()
                Image.fromarray(overlay_np).save(buffered, format="PNG")
                gradcam_b64 = base64.b64encode(buffered.getvalue()).decode()
                
            except Exception as e:
                print(f"  Grad-CAM error: {e}")
                import traceback
                traceback.print_exc()
            
            # Build response
            result = {
                "prediction_class": pred_label,
                "tumor_probability": round(tumor_prob, 4),
                "confidence": policy["confidence"],
                "confidence_score": round(conf_score, 4),
                "mc_uncertainty": round(uncertainty, 4),
                "mc_uncertainty_per_class": {
                    self.labels[i]: round(float(std_probs[i]), 4)
                    for i in range(len(std_probs))
                },
                "mc_passes": self.mc_passes,
                "requires_human_review": policy["requires_human_review"],
                "review_message": policy["review_message"],
                # Simple format for frontend compatibility
                "probabilities": {
                    self.labels[i]: round(float(mean_probs[i]), 4)
                    for i in range(len(mean_probs))
                },
                "gradcam_image": f"data:image/png;base64,{gradcam_b64}" if gradcam_b64 else None,
                "model_version": "v0.1.0",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            
            return result
            
        except Exception as e:
            print(f"Error during Grad-CAM prediction: {e}")
            import traceback
            traceback.print_exc()
            return {
                "prediction_class": "error",
                "confidence": 0.0,
                "probabilities": {"error": str(e)},
                "gradcam_image": None,
                "mc_uncertainty": None,
                "requires_human_review": True,
                "review_message": str(e)
            }


# Global model loader instance
model_loader = ModelLoader()
