# Candor Dust - AI Model (ViT)

## 🧠 System Overview

The **Candor Dust AI Engine** utilizes a **Vision Transformer (ViT)** architecture for high-precision brain tumor classification. Unlike traditional CNNs, the ViT treats image patches as sequences, allowing it to capture global dependencies across medical scans.

### Model Details
- **Base Architecture**: `google/vit-base-patch16-224-in21k`
- **Framework**: Developed using **PyTorch** and **Hugging Face Transformers**.
- **Input Specification**: 224x224 RGB MRI scans.
- **Classification Categories**:
  - `glioma`: Tumors in the glial cells.
  - `meningioma`: Tumors in the meninges.
  - `pituitary`: Tumors in the pituitary gland.
  - `no_tumor`: Healthy brain tissue.

## 🏋️ Monitoring & Training (`train.py`)

The `train.py` script is a comprehensive pipeline for fine-tuning the ViT model on custom medical datasets.

### Key Features of the Training Pipeline:
- **Stratified Splitting**: Automatically splits the dataset into 70% Train, 15% Val, and 15% Test while maintaining class balance to prevent data leakage.
- **Efficient Fine-tuning**: Freezes the early transformer blocks and embeddings to reduce memory usage, making it trainable on 6GB-8GB GPUs.
- **Monte Carlo Dropout**: Integrated support for uncertainty quantification during inference.
- **Artifact Versioning**: Saves the fine-tuned weights, processor configs, and a full evaluation report (confusion matrix, ROC curves) in a versioned folder (e.g., `brain_tumor_vit_v0.1.0/`).

### How to Start Training:
1. **Prepare Environment**: Use `uv sync` to install dependencies.
2. **Execute**:
   ```bash
   uv run python train.py
   ```
   *Note: Ensure you have a GPU available or adjust the `fp16` setting in the script's `CONFIG` for CPU training.*

## 🚀 Serving & Inference

### Local/Ray Inference (`serve.py`)
The `serve.py` script handles the production-ready serving of the model.

1. **Start the Service**:
   ```bash
   uv run python serve.py
   ```
2. **Production Scaling**: The script uses **Ray Serve**, allowing the model to be deployed as a scalable service that can handle concurrent requests across multiple GPU nodes.

## 🛠️ Configuration (.env)

The model module may require Hugging Face credentials for dataset access or model uploads:

| Variable | Description |
|----------|-------------|
| `HF_TOKEN` | Your Hugging Face access token for repo uploads. |
| `HF_USERNAME` | Your Hugging Face username. |

---
*For the full system overview, see the root [README.md](../README.md).*
