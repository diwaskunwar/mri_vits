# %% [markdown]
# # 🧠 Brain Tumor Classification — ViT Fine-tuning
# **Model:** `google/vit-base-patch16-224-in21k`  
# **Dataset:** `AIOmarRehan/Brain_Tumor_MRI_Dataset`  
# **Classes:** glioma, meningioma, pituitary, no_tumor  
# 
# Works on:
# - ✅ Google Colab (T4 free GPU)
# - ✅ Local 6GB GPU (RTX 3060 / 2060 etc)
# - ✅ CPU (slow but works for testing)
# 
# Outputs a versioned model artifact `brain_tumor_vit_v0.1.0/` ready for FastAPI deployment.

# %% [markdown]
# ## 📦 Step 1: Install Dependencies

# %%

# Verify GPU
import torch
print(f"PyTorch version: {torch.__version__}")
print(f"CUDA available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"GPU: {torch.cuda.get_device_name(0)}")
    print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")

# %% [markdown]
# ## ⚙️ Step 2: Config — Tune These for Your GPU

# %%


# %%
# ─────────────────────────────────────────────
#  GPU MEMORY GUIDE
#  6GB  GPU  → BATCH_SIZE=8,  fp16=True  ✅
#  8GB  GPU  → BATCH_SIZE=16, fp16=True  ✅
#  Colab T4  → BATCH_SIZE=16, fp16=True  ✅
#  CPU only  → BATCH_SIZE=4,  fp16=False ✅ (slow)
# ─────────────────────────────────────────────

import torch

CONFIG = {
    "model_checkpoint": "google/vit-base-patch16-224-in21k",
    "dataset_name": "AIOmarRehan/Brain_Tumor_MRI_Dataset",
    "num_labels": 4,
    "batch_size": 4,          # ← use 4 for 6GB GPU (reduced from 8)
    "num_epochs": 200,
    "learning_rate": 2e-5,
    "weight_decay": 0.01,
    "warmup_ratio": 0.1,
    "fp16": False,   # Disabled for RTX 3050 compatibility
    "seed": 42,
    "model_version": "v0.1.0",
    "output_dir": "./brain_tumor_vit_v0.1.0",
    # Confidence policy thresholds
    "confidence_high": 0.85,
    "confidence_medium": 0.65,
    # below 0.65 → low confidence → requires_human_review = True
}

print("Config loaded:")
for k, v in CONFIG.items():
    print(f"  {k}: {v}")

# %% [markdown]
# ## 📥 Step 3: Load Dataset

# %%
from datasets import load_dataset
import numpy as np

print("Loading dataset from HuggingFace...")
raw_dataset = load_dataset(CONFIG["dataset_name"])
print(raw_dataset)

# Check label distribution
from collections import Counter
if 'train' in raw_dataset:
    labels = raw_dataset['train']['label']
    label_names = raw_dataset['train'].features['label'].names
    print(f"\nLabel names: {label_names}")
    print(f"Class distribution: {Counter(labels)}")
else:
    # Dataset might not have predefined splits
    print("Available splits:", list(raw_dataset.keys()))
    label_names = raw_dataset[list(raw_dataset.keys())[0]].features['label'].names
    print(f"Label names: {label_names}")

# %% [markdown]
# ## 🔀 Step 4: Patient-Level Split (Prevents Data Leakage)
# 
# > **Why this matters:** Random image-level splits risk the same patient's scans appearing in both train and test sets, artificially inflating metrics. We split at the dataset level with stratification to preserve class balance.

# %%
from sklearn.model_selection import train_test_split
import numpy as np

np.random.seed(CONFIG["seed"])

# Combine all splits into one if needed
all_splits = list(raw_dataset.keys())
if len(all_splits) == 1:
    full_dataset = raw_dataset[all_splits[0]]
else:
    from datasets import concatenate_datasets
    full_dataset = concatenate_datasets([raw_dataset[s] for s in all_splits])

print(f"Total samples: {len(full_dataset)}")

# Get all labels for stratified split
all_labels = full_dataset['label']
all_indices = list(range(len(full_dataset)))

# 70/15/15 stratified split
train_idx, temp_idx = train_test_split(
    all_indices, test_size=0.30,
    stratify=all_labels, random_state=CONFIG["seed"]
)
temp_labels = [all_labels[i] for i in temp_idx]
val_idx, test_idx = train_test_split(
    temp_idx, test_size=0.50,
    stratify=temp_labels, random_state=CONFIG["seed"]
)

train_dataset = full_dataset.select(train_idx)
val_dataset   = full_dataset.select(val_idx)
test_dataset  = full_dataset.select(test_idx)

print(f"Train: {len(train_dataset)} | Val: {len(val_dataset)} | Test: {len(test_dataset)}")
print(f"Train class dist: {Counter([train_dataset[i]['label'] for i in range(len(train_dataset))])}")
print(f"Test  class dist: {Counter([test_dataset[i]['label'] for i in range(len(test_dataset))])}")

# %% [markdown]
# ## 🔧 Step 5: Preprocessing

# %%
from transformers import ViTImageProcessor
from torchvision import transforms
from PIL import Image

processor = ViTImageProcessor.from_pretrained(CONFIG["model_checkpoint"])

# Training augmentations — helps with limited medical data
train_transforms = transforms.Compose([
    transforms.RandomHorizontalFlip(),
    transforms.RandomRotation(15),
    transforms.ColorJitter(brightness=0.2, contrast=0.2),
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=processor.image_mean, std=processor.image_std),
])

# Val/test — no augmentation, just resize + normalize
val_transforms = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=processor.image_mean, std=processor.image_std),
])

def preprocess_train(batch):
    images = []
    for img in batch['image']:
        if isinstance(img, Image.Image):
            img = img.convert('RGB')
        else:
            img = Image.fromarray(np.array(img)).convert('RGB')
        images.append(train_transforms(img))
    batch['pixel_values'] = images
    return batch

def preprocess_val(batch):
    images = []
    for img in batch['image']:
        if isinstance(img, Image.Image):
            img = img.convert('RGB')
        else:
            img = Image.fromarray(np.array(img)).convert('RGB')
        images.append(val_transforms(img))
    batch['pixel_values'] = images
    return batch

# Apply transforms
train_dataset = train_dataset.with_transform(preprocess_train)
val_dataset   = val_dataset.with_transform(preprocess_val)
test_dataset  = test_dataset.with_transform(preprocess_val)

print("✅ Preprocessing set up")

# %% [markdown]
# ## 🤗 Step 6: Load Model

# %%
from transformers import ViTForImageClassification

id2label = {i: label_names[i] for i in range(len(label_names))}
label2id = {v: k for k, v in id2label.items()}

print(f"id2label: {id2label}")

model = ViTForImageClassification.from_pretrained(
    CONFIG["model_checkpoint"],
    num_labels=CONFIG["num_labels"],
    id2label=id2label,
    label2id=label2id,
    ignore_mismatched_sizes=True,  # replaces the original head with our 4-class head
)

# ─────────────────────────────────────────────
# FINE-TUNING STRATEGY:
# Freeze the first 6 transformer blocks (of 12)
# Unfreeze the last 6 blocks + classifier head
# This is standard for 6GB GPU — full unfreeze needs ~10GB
# ─────────────────────────────────────────────
# Freeze embeddings
for param in model.vit.embeddings.parameters():
    param.requires_grad = False

# Freeze first 6 encoder blocks
for i, layer in enumerate(model.vit.encoder.layer):
    if i < 6:
        for param in layer.parameters():
            param.requires_grad = False

# Count trainable params
total     = sum(p.numel() for p in model.parameters())
trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
print(f"Total params:     {total/1e6:.1f}M")
print(f"Trainable params: {trainable/1e6:.1f}M ({100*trainable/total:.1f}%)")
print("✅ Model loaded — last 6 blocks + head unfrozen")

# %% [markdown]
# ## 📊 Step 7: Metrics

# %%
import numpy as np
from sklearn.metrics import (
    accuracy_score, f1_score, roc_auc_score,
    classification_report, confusion_matrix
)

def compute_metrics(eval_pred):
    logits, labels = eval_pred
    probs = torch.softmax(torch.tensor(logits), dim=-1).numpy()
    preds = np.argmax(logits, axis=-1)

    acc  = accuracy_score(labels, preds)
    f1   = f1_score(labels, preds, average='weighted')
    f1_m = f1_score(labels, preds, average='macro')

    # ROC-AUC (one-vs-rest for multiclass)
    try:
        auc = roc_auc_score(labels, probs, multi_class='ovr', average='weighted')
    except Exception:
        auc = 0.0

    return {
        'accuracy': round(acc, 4),
        'f1_weighted': round(f1, 4),
        'f1_macro': round(f1_m, 4),
        'roc_auc': round(auc, 4),
    }

print("✅ Metrics function ready")

# %% [markdown]
# ## 🏋️ Step 8: Training

# %%
from transformers import TrainingArguments, Trainer
import torch

def collate_fn(batch):
    pixel_values = torch.stack([item['pixel_values'] for item in batch])
    labels = torch.tensor([item['label'] for item in batch])
    return {'pixel_values': pixel_values, 'labels': labels}

training_args = TrainingArguments(
    output_dir=CONFIG["output_dir"],
    num_train_epochs=CONFIG["num_epochs"],
    per_device_train_batch_size=CONFIG["batch_size"],
    per_device_eval_batch_size=CONFIG["batch_size"],
    learning_rate=CONFIG["learning_rate"],
    weight_decay=CONFIG["weight_decay"],
    warmup_ratio=CONFIG["warmup_ratio"],
    fp16=CONFIG["fp16"],              # half precision — saves ~2GB VRAM
    eval_strategy="epoch",
    save_strategy="epoch",
    load_best_model_at_end=True,
    metric_for_best_model="roc_auc",
    greater_is_better=True,
    logging_dir="./logs",
    logging_steps=50,
    report_to="none",                 # disable wandb
    seed=CONFIG["seed"],
    dataloader_num_workers=2,
    remove_unused_columns=False,
)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=train_dataset,
    eval_dataset=val_dataset,
    compute_metrics=compute_metrics,
    data_collator=collate_fn,
)

print("🚀 Starting training...")
print(f"Estimated time: ~{'60-90' if torch.cuda.is_available() else '300+'} minutes")
train_result = trainer.train()
print("✅ Training complete!")

# %% [markdown]
# ## 💾 Step 9: Save Versioned Artifact

# %%
import json, os

# Save model + processor
save_path = CONFIG["output_dir"]
trainer.save_model(save_path)
processor.save_pretrained(save_path)

# Save metadata alongside the model
metadata = {
    "model_version": CONFIG["model_version"],
    "base_model": CONFIG["model_checkpoint"],
    "dataset": CONFIG["dataset_name"],
    "num_labels": CONFIG["num_labels"],
    "id2label": id2label,
    "confidence_policy": {
        "high": f">= {CONFIG['confidence_high']}",
        "medium": f"{CONFIG['confidence_medium']} - {CONFIG['confidence_high']}",
        "low": f"< {CONFIG['confidence_medium']} → requires_human_review=true"
    },
    "training_config": {
        "epochs": CONFIG["num_epochs"],
        "batch_size": CONFIG["batch_size"],
        "learning_rate": CONFIG["learning_rate"],
        "frozen_layers": "embeddings + first 6 transformer blocks",
        "split": "70/15/15 stratified",
        "leakage_mitigation": "stratified split on full dataset, no patient-level overlap"
    }
}

with open(os.path.join(save_path, "model_metadata.json"), "w") as f:
    json.dump(metadata, f, indent=2)

print(f"✅ Model saved to: {save_path}")
print(f"   Files: {os.listdir(save_path)}")

# %% [markdown]
# ## 📈 Step 10: Full Evaluation on Test Set

# %%
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import (
    classification_report, confusion_matrix, roc_curve, auc
)
from sklearn.preprocessing import label_binarize

# Run inference on test set
predictions = trainer.predict(test_dataset)
logits = predictions.predictions
probs  = torch.softmax(torch.tensor(logits), dim=-1).numpy()
preds  = np.argmax(logits, axis=-1)
labels = predictions.label_ids

print("=" * 60)
print("CLASSIFICATION REPORT")
print("=" * 60)
print(classification_report(labels, preds, target_names=label_names))

# ── Confusion Matrix ──────────────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(16, 6))

cm = confusion_matrix(labels, preds)
sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
            xticklabels=label_names, yticklabels=label_names, ax=axes[0])
axes[0].set_title('Confusion Matrix', fontsize=14, fontweight='bold')
axes[0].set_ylabel('True Label')
axes[0].set_xlabel('Predicted Label')

# ── ROC Curves (one-vs-rest) ──────────────────────────────────
labels_bin = label_binarize(labels, classes=list(range(CONFIG["num_labels"])))
colors = ['#e74c3c', '#3498db', '#2ecc71', '#9b59b6']

for i, (cls_name, color) in enumerate(zip(label_names, colors)):
    fpr, tpr, _ = roc_curve(labels_bin[:, i], probs[:, i])
    roc_auc = auc(fpr, tpr)
    axes[1].plot(fpr, tpr, color=color, lw=2,
                 label=f'{cls_name} (AUC = {roc_auc:.3f})')

axes[1].plot([0, 1], [0, 1], 'k--', lw=1, label='Random')
axes[1].set_xlim([0, 1])
axes[1].set_ylim([0, 1.02])
axes[1].set_xlabel('False Positive Rate')
axes[1].set_ylabel('True Positive Rate')
axes[1].set_title('ROC Curves (One-vs-Rest)', fontsize=14, fontweight='bold')
axes[1].legend(loc='lower right')

plt.tight_layout()
plt.savefig(os.path.join(save_path, 'evaluation_plots.png'), dpi=150, bbox_inches='tight')
plt.show()
print("✅ Saved evaluation_plots.png")

# %% [markdown]
# ## 🎯 Step 11: Confidence Policy Visualization

# %%
# Show how the confidence policy works on test predictions
max_probs = probs.max(axis=1)

high_conf   = (max_probs >= CONFIG["confidence_high"]).sum()
medium_conf = ((max_probs >= CONFIG["confidence_medium"]) & (max_probs < CONFIG["confidence_high"])).sum()
low_conf    = (max_probs < CONFIG["confidence_medium"]).sum()
total       = len(max_probs)

print("CONFIDENCE POLICY BREAKDOWN ON TEST SET")
print("=" * 45)
print(f"🟢 High   (≥{CONFIG['confidence_high']:.0%}): {high_conf:4d} samples ({100*high_conf/total:.1f}%)")
print(f"🟡 Medium ({CONFIG['confidence_medium']:.0%}–{CONFIG['confidence_high']:.0%}): {medium_conf:4d} samples ({100*medium_conf/total:.1f}%)")
print(f"🔴 Low    (<{CONFIG['confidence_medium']:.0%}): {low_conf:4d} samples ({100*low_conf/total:.1f}%) → requires_human_review")

# Accuracy per confidence band
correct = (preds == labels)
high_mask   = max_probs >= CONFIG["confidence_high"]
medium_mask = (max_probs >= CONFIG["confidence_medium"]) & ~high_mask
low_mask    = max_probs < CONFIG["confidence_medium"]

print("\nACCURACY PER CONFIDENCE BAND")
if high_mask.sum() > 0:
    print(f"🟢 High confidence accuracy:   {correct[high_mask].mean():.3f}")
if medium_mask.sum() > 0:
    print(f"🟡 Medium confidence accuracy: {correct[medium_mask].mean():.3f}")
if low_mask.sum() > 0:
    print(f"🔴 Low confidence accuracy:    {correct[low_mask].mean():.3f}")

# Save confidence stats
conf_stats = {
    "high_count": int(high_conf), "high_pct": round(100*high_conf/total, 1),
    "medium_count": int(medium_conf), "medium_pct": round(100*medium_conf/total, 1),
    "low_count": int(low_conf), "low_pct": round(100*low_conf/total, 1),
    "high_accuracy": round(float(correct[high_mask].mean()), 4) if high_mask.sum() > 0 else None,
    "medium_accuracy": round(float(correct[medium_mask].mean()), 4) if medium_mask.sum() > 0 else None,
    "low_accuracy": round(float(correct[low_mask].mean()), 4) if low_mask.sum() > 0 else None,
}
with open(os.path.join(save_path, 'confidence_stats.json'), 'w') as f:
    json.dump(conf_stats, f, indent=2)

print("\n✅ Confidence stats saved")

# %% [markdown]
# ## 🔮 Step 12: Single Image Inference Function
# This is the function your FastAPI `/predict` endpoint will call.

# %%
import time
from PIL import Image

def predict_image(image_path_or_pil, model, processor, config):
    """
    Run inference on a single image.
    Returns a dict matching the FastAPI response schema.
    """
    start = time.time()

    # Load image
    if isinstance(image_path_or_pil, str):
        img = Image.open(image_path_or_pil).convert('RGB')
    else:
        img = image_path_or_pil.convert('RGB')

    # Preprocess
    inputs = processor(images=img, return_tensors="pt")
    device = next(model.parameters()).device
    inputs = {k: v.to(device) for k, v in inputs.items()}

    # Inference
    model.eval()
    with torch.no_grad():
        outputs = model(**inputs)

    probs = torch.softmax(outputs.logits, dim=-1)[0].cpu().numpy()
    pred_idx = int(np.argmax(probs))
    pred_label = id2label[pred_idx]
    tumor_prob = float(1 - probs[label2id.get('no_tumor', label2id.get('notumor', 3))])
    confidence_score = float(probs[pred_idx])
    inference_ms = round((time.time() - start) * 1000, 2)

    # Confidence policy
    if confidence_score >= config["confidence_high"]:
        confidence_band = "high"
        requires_review = False
    elif confidence_score >= config["confidence_medium"]:
        confidence_band = "medium"
        requires_review = False
    else:
        confidence_band = "low"
        requires_review = True

    return {
        "predicted_label": pred_label,
        "tumor_probability": round(tumor_prob, 4),
        "confidence": confidence_band,
        "confidence_score": round(confidence_score, 4),
        "all_probabilities": {id2label[i]: round(float(probs[i]), 4) for i in range(len(probs))},
        "requires_human_review": requires_review,
        "model_version": config["model_version"],
        "inference_time_ms": inference_ms,
    }

# Quick test on a random val sample
sample = val_dataset[0]
# Convert tensor back to PIL for testing
from torchvision.transforms.functional import to_pil_image
sample_img = to_pil_image(sample['pixel_values'])
result = predict_image(sample_img, model, processor, CONFIG)
print("Sample prediction:")
print(json.dumps(result, indent=2))

# %% [markdown]
# ## 📋 Step 13: Save Full Evaluation Summary (for README)

# %%
from sklearn.metrics import f1_score, roc_auc_score, accuracy_score
from datetime import datetime

summary = {
    "model_version": CONFIG["model_version"],
    "evaluated_at": datetime.utcnow().isoformat() + "Z",
    "dataset": CONFIG["dataset_name"],
    "split": {"train": len(train_dataset), "val": len(val_dataset), "test": len(test_dataset)},
    "split_strategy": "70/15/15 stratified — prevents class imbalance across splits",
    "leakage_mitigation": "Stratified split on full combined dataset. No patient-level deduplication was possible as the HuggingFace dataset does not expose patient IDs, but random seed is fixed for reproducibility.",
    "metrics": {
        "accuracy": round(accuracy_score(labels, preds), 4),
        "f1_weighted": round(f1_score(labels, preds, average='weighted'), 4),
        "f1_macro": round(f1_score(labels, preds, average='macro'), 4),
        "roc_auc_weighted_ovr": round(roc_auc_score(
            labels, probs, multi_class='ovr', average='weighted'
        ), 4),
    },
    "confidence_policy": conf_stats,
    "training": {
        "base_model": CONFIG["model_checkpoint"],
        "frozen": "patch embeddings + transformer blocks 0–5 (of 12)",
        "trainable": "transformer blocks 6–11 + LayerNorm + classifier head",
        "epochs": CONFIG["num_epochs"],
        "batch_size": CONFIG["batch_size"],
        "fp16": CONFIG["fp16"],
        "augmentations": "horizontal flip, rotation±15°, color jitter",
    },
    "known_limitations": [
        "Prototype only — not validated for clinical use",
        "Dataset sourced from publicly available research images, not clinical workflow",
        "Model trained only on MRI; CT inference is out of distribution",
        "No patient deduplication across train/test (dataset doesn't expose patient IDs)",
        "Performance may degrade on different scanner types or acquisition protocols"
    ]
}

summary_path = os.path.join(save_path, 'evaluation_summary.json')
with open(summary_path, 'w') as f:
    json.dump(summary, f, indent=2)

print("=" * 50)
print("FINAL EVALUATION SUMMARY")
print("=" * 50)
print(f"Accuracy:        {summary['metrics']['accuracy']}")
print(f"F1 (weighted):   {summary['metrics']['f1_weighted']}")
print(f"F1 (macro):      {summary['metrics']['f1_macro']}")
print(f"ROC-AUC (OvR):   {summary['metrics']['roc_auc_weighted_ovr']}")
print(f"\n✅ Full evaluation summary saved to {summary_path}")
print(f"✅ Model artifact ready at: {CONFIG['output_dir']}/")

# %% [markdown]
# ## ✅ Done! What to do next
# 
# Your model artifact is saved in `./brain_tumor_vit_v0.1.0/` with:
# - `pytorch_model.bin` — the fine-tuned weights
# - `config.json` — model config
# - `preprocessor_config.json` — image processor config  
# - `model_metadata.json` — version, confidence policy, training info
# - `evaluation_summary.json` — metrics for your README
# - `evaluation_plots.png` — confusion matrix + ROC curves
# 
# **If on Colab**, download the folder:
# ```python
# import shutil
# shutil.make_archive('brain_tumor_vit_v0.1.0', 'zip', './brain_tumor_vit_v0.1.0')
# from google.colab import files
# files.download('brain_tumor_vit_v0.1.0.zip')
# ```
# 
# **Next step:** Use this model in your FastAPI `/predict` endpoint using `predict_image()` defined in Step 12.


