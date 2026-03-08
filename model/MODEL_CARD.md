---
pipeline_tag: image-classification
tags:
- medical
- brain-tumor
- vision
- candor-dust
license: mit
---

# Brain Tumor Classification ViT (Candor Dust)

This is a Vision Transformer (ViT) fine-tuned for classifying brain MRI scans into four categories:
1. `glioma`
2. `meningioma`
3. `notumor`
4. `pituitary`

## Model Description
The model is based on `google/vit-base-patch16-224-in21k` and fine-tuned on a dataset of brain MRI scans. It is used as the core classification engine in the **Candor Dust** application.

## Intended Use
- **Primary Use Case:** Research prototype for AI-assisted brain tumor classification.
- **Out of Scope Use:** This model is **NOT** a certified medical device and should not be used for direct clinical diagnosis without human oversight.

## Uncertainty & Explainability
This model deployment includes:
- **Monte Carlo (MC) Dropout:** During inference, the model runs 20 passes with dropout enabled to estimate predictive uncertainty. High uncertainty triggers a "Requires Human Review" alert.
- **Grad-CAM (Gradient-weighted Class Activation Mapping):** Generates heatmaps indicating which regions of the MRI scan contributed most to the prediction.

## Usage
You can load the model directly via the `transformers` library:

```python
from transformers import ViTForImageClassification, ViTImageProcessor
import torch
from PIL import Image

model_name = "diwaskunwar10/brain-tumor-vit-candor"
processor = ViTImageProcessor.from_pretrained(model_name)
model = ViTForImageClassification.from_pretrained(model_name)

image = Image.open("path_to_mri.jpg").convert("RGB")
inputs = processor(images=image, return_tensors="pt")
with torch.no_grad():
    outputs = model(**inputs)
    probs = torch.nn.functional.softmax(outputs.logits, dim=-1)
    predicted_class = probs.argmax(-1).item()
    print(model.config.id2label[predicted_class])
```

## Disclaimer
⚠️ **RESEARCH PROTOTYPE ONLY** — NOT a certified medical device. Not for clinical use. Always consult qualified healthcare professionals for medical decisions.
