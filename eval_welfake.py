"""
WelFake Cross-Domain Evaluation — Batch Vectorized (Fast)
Tests the production model on the WelFake dataset using batch inference.
"""
import sys, os, io, time, warnings

# Suppress LightGBM/sklearn warnings
warnings.filterwarnings("ignore")
os.environ["PYTHONWARNINGS"] = "ignore"

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import numpy as np
import pandas as pd
from pathlib import Path
from joblib import load
from scipy.sparse import hstack, csr_matrix

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils import clean_text
from meta_features import extract_single as compute_meta_features

print("=" * 70)
print("  WelFake Cross-Domain Evaluation (Batch Vectorized)")
print("  Testing production model on 72,134 unseen articles")
print("=" * 70)

# ── Load Dataset ──
DATA_PATH = Path(__file__).resolve().parent / "data_new" / "WELFake_Dataset.csv"
print(f"\n[1/5] Loading dataset: {DATA_PATH.name}")
df = pd.read_csv(DATA_PATH)
print(f"  Raw rows: {len(df):,}")

df = df.dropna(subset=["text", "label"])
df["text"] = df["text"].astype(str)
df = df[df["text"].str.strip().str.len() > 20]
df["label"] = df["label"].astype(int)

# CRITICAL: WelFake uses 0=real, 1=fake (confirmed by inspecting titles)
# Our model convention: 0=FAKE, 1=REAL (verified via train.py line 170)
# Invert labels: WelFake 0(real)→1(REAL), WelFake 1(fake)→0(FAKE)
df["label"] = df["label"].map({0: 1, 1: 0})
df = df.dropna(subset=["label"])
df["label"] = df["label"].astype(int)

print(f"  Usable rows: {len(df):,}")
print(f"  After label mapping (our convention: 0=FAKE, 1=REAL):")
print(f"    0=Fake: {(df['label']==0).sum():,}  |  1=Real: {(df['label']==1).sum():,}")

# ── Load Model ──
print("\n[2/5] Loading production model...")
MODEL_DIR = Path(__file__).resolve().parent / "models"
model = load(MODEL_DIR / "model.joblib")
tfidf = load(MODEL_DIR / "tfidf.joblib")
scaler = load(MODEL_DIR / "scaler.joblib")
print("  Loaded: model.joblib + tfidf.joblib + scaler.joblib")

# ── Sample ──
SAMPLE_SIZE = 5000
print(f"\n[3/5] Stratified sampling {SAMPLE_SIZE:,} articles...")
n_per_class = SAMPLE_SIZE // 2
df_fake = df[df["label"] == 0].sample(n=min(len(df[df["label"]==0]), n_per_class), random_state=42)
df_real = df[df["label"] == 1].sample(n=min(len(df[df["label"]==1]), n_per_class), random_state=42)
df_sample = pd.concat([df_fake, df_real]).reset_index(drop=True)
print(f"  Sampled: {len(df_sample):,} (Fake={len(df_fake):,}, Real={len(df_real):,})")

# ── Batch Inference ──
print(f"\n[4/5] Running batch inference...")
start = time.time()

texts = df_sample["text"].tolist()
y_true = df_sample["label"].values

# Step 1: Clean all texts
print("  Cleaning texts...")
cleaned = [clean_text(t) for t in texts]

# Step 2: TF-IDF transform (batch)
print("  TF-IDF vectorizing...")
X_tfidf = tfidf.transform(cleaned)

# Step 3: Meta features (batch)
print("  Computing meta features...")
meta_list = []
for i, t in enumerate(texts):
    try:
        meta_list.append(compute_meta_features(t).flatten())
    except:
        meta_list.append(np.zeros(20))  # fallback
    if (i+1) % 1000 == 0:
        print(f"    meta features: {i+1:,}/{len(texts):,}")
meta_arr = np.vstack(meta_list)
X_meta = scaler.transform(meta_arr)

# Step 4: Combine features
X_combined = hstack([X_tfidf, csr_matrix(X_meta)])
print(f"  Feature matrix: {X_combined.shape}")

# Step 5: Predict (batch)
print("  Running ensemble prediction...")
proba = model.predict_proba(X_combined)
# Convention: classes_ = [FAKE=0, REAL=1]
fake_probs = proba[:, 0]
real_probs = proba[:, 1]
y_pred = (real_probs > 0.5).astype(int)  # 1=REAL, 0=FAKE
y_conf = np.maximum(fake_probs, real_probs) * 100

elapsed = time.time() - start
print(f"  Done: {len(y_pred):,} predictions in {elapsed:.1f}s ({len(y_pred)/elapsed:.0f}/sec)")

# ── Metrics ──
print("\n[5/5] Computing metrics...")
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, confusion_matrix, classification_report
)

accuracy = accuracy_score(y_true, y_pred)
precision = precision_score(y_true, y_pred, zero_division=0)
recall = recall_score(y_true, y_pred, zero_division=0)
f1 = f1_score(y_true, y_pred, zero_division=0)
try:
    roc_auc = roc_auc_score(y_true, real_probs)
except:
    roc_auc = 0.0

cm = confusion_matrix(y_true, y_pred)

print("\n" + "=" * 70)
print("  WELFAKE CROSS-DOMAIN EVALUATION RESULTS")
print("=" * 70)
print(f"\n  Dataset:     WelFake (72,134 articles, 4 merged sources)")
print(f"  Evaluated:   {len(y_true):,} articles (stratified sample)")
print(f"  Inference:   {elapsed:.1f}s ({len(y_true)/elapsed:.0f} articles/sec)")
print(f"\n  {'Metric':<20} {'Score':>10}")
print(f"  {'-'*32}")
print(f"  {'Accuracy':<20} {accuracy*100:>9.2f}%")
print(f"  {'Precision (Real)':<20} {precision*100:>9.2f}%")
print(f"  {'Recall (Real)':<20} {recall*100:>9.2f}%")
print(f"  {'F1-Score':<20} {f1*100:>9.2f}%")
print(f"  {'ROC-AUC':<20} {roc_auc*100:>9.2f}%")
print(f"  {'Avg Confidence':<20} {y_conf.mean():>9.2f}%")

print(f"\n  Confusion Matrix:")
print(f"                    Predicted")
print(f"                    FAKE     REAL")
print(f"  Actual FAKE    [{cm[0][0]:>6,}   {cm[0][1]:>6,}]")
print(f"  Actual REAL    [{cm[1][0]:>6,}   {cm[1][1]:>6,}]")

print(f"\n  Classification Report:")
print(classification_report(y_true, y_pred, target_names=["FAKE (0)", "REAL (1)"]))

# ── Confidence Distribution ──
high = (y_conf >= 90).sum()
med = ((y_conf >= 70) & (y_conf < 90)).sum()
low = ((y_conf >= 50) & (y_conf < 70)).sum()
border = (y_conf < 50).sum()
n = len(y_conf)

print(f"  Confidence Distribution:")
print(f"    High (>=90%):      {high:>5,}  ({high/n*100:.1f}%)")
print(f"    Medium (70-90%):   {med:>5,}  ({med/n*100:.1f}%)")
print(f"    Low (50-70%):      {low:>5,}  ({low/n*100:.1f}%)")
print(f"    Borderline (<50%): {border:>5,}  ({border/n*100:.1f}%)")

if high > 0:
    hc_mask = y_conf >= 90
    hc_acc = accuracy_score(y_true[hc_mask], y_pred[hc_mask])
    print(f"\n  High-confidence accuracy (>=90%): {hc_acc*100:.2f}%")

if med > 0:
    mc_mask = (y_conf >= 70) & (y_conf < 90)
    mc_acc = accuracy_score(y_true[mc_mask], y_pred[mc_mask])
    print(f"  Medium-confidence accuracy (70-90%): {mc_acc*100:.2f}%")

# ── Per-class accuracy ──
fake_mask = y_true == 0
real_mask = y_true == 1
fake_acc = accuracy_score(y_true[fake_mask], y_pred[fake_mask]) if fake_mask.sum() > 0 else 0
real_acc = accuracy_score(y_true[real_mask], y_pred[real_mask]) if real_mask.sum() > 0 else 0
print(f"\n  Per-class Accuracy:")
print(f"    Fake articles correctly identified: {fake_acc*100:.2f}%")
print(f"    Real articles correctly identified: {real_acc*100:.2f}%")

print("\n" + "=" * 70)
print("  Evaluation complete!")
print("=" * 70)
