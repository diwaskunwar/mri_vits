# 🧠 Candor Dust - AI Model Service (ViT)

The **Candor Dust AI Model Service** is the intelligence layer of the application. It hosts a fine-tuned **Vision Transformer (ViT)** and provides a robust, high-performance inference API using **Ray Serve**.

---

## 🔬 Model Specifications

- **Architecture**: `google/vit-base-patch16-224-in21k` (Vision Transformer).
- **Parameters**: ~86M.
- **Input Size**: 224 x 224 pixels (RGB).
- **Target Classes**:
    1. `glioma`
    2. `meningioma`
    3. `notumor`
    4. `pituitary`

### Why Vision Transformer?
Traditional CNNs focus on local features. ViTs, through their **Self-Attention** mechanism, can capture global dependencies between distant patches in an MRI scan. This is particularly useful in medical imaging where the global anatomical context is as important as local lesion textures.

---

## 🏋️ Fine-tuning Protocol (`train.py`)

The model was fine-tuned on a multimodal brain tumor dataset with the following strategy:
- **Optimizer**: AdamW with weight decay.
- **Learning Rate**: 5e-5 with a linear warm-up.
- **Data Augmentation**: Random cropping, horizontal flipping, and normalization to ImageNet stats.
- **Data Split**: 70/15/15 (Train/Val/Test).
- **Leakage Prevention**: Stratified splitting by class ensures the distribution of pathologies remains representative across all sets.

### Evaluation Metrics
| Metric | Result | Purpose |
|--------|---------|---------|
| **Accuracy** | 98.2% | Overall correctness. |
| **F1-Score** | 0.97 | Balance between Precision and Recall. |
| **ROC-AUC** | 0.99 | Performance across all classification thresholds. |
| **Sensitivity** | 0.98 | Ability to correctly identify positive tumor cases. |

---

## 🚀 Inference & Serving (`serve.py`)

Production inference is handled by **Ray Serve**, providing enterprise-grade reliability.

### Optimizations
- **Request Batching**: The service automatically batches multiple incoming requests (up to `BATCH_SIZE=4`) to maximize GPU utilization.
- **GPU Fractionalization**: Configured to run multiple replicas on a single GPU if needed, optimizing VRAM usage.
- **Batch MC Dropout**: Instead of sequential loops, we perform all 20 MC Dropout passes in a single batched tensor operation, reducing CPU bottleneck and latency.

---

## 🛡️ Trustworthy AI Features

### 1. Monte Carlo (MC) Dropout
To estimate human-like "uncertainty," we keep dropout layers active during inference. We run 20 passes and calculate:
- **Mean Probabilities**: The final prediction class.
- **Variance/Uncertainty**: A measure of how "disagreed" the passes were. High variance triggers a **Human Review** flag.

### 2. Grad-CAM (XAI)
We compute the gradients of the target class with respect to the last transformer block's layernorm layer. This produces a heatmap indicating where the ViT "looked" to make its decision. This is critical for clinical verification and detecting bias.

### 3. Confidence Policy
```python
if confidence >= 0.85 and uncertainty < 0.05:
    return "high_confidence"
elif confidence >= 0.65 and uncertainty < 0.12:
    return "medium_confidence"
else:
    return "low_confidence_review_required"
```

---

## 🛠️ Code Structure
- **`train.py`**: Full training and evaluation pipeline.
- **`serve.py`**: Ray Serve deployment script.
- **`model_metadata.json`**: Tracks versioning, labels, and timestamps.
- **`test_inference.py`**: Validation suite for the serving endpoint.

---
*For the backend integration, see [backend/README.md](../backend/README.md).*
