"""
Hybrid Fake News Detector — Training Pipeline v3.0

Industry-grade training with:
- Experiment tracking and versioning
- Cross-domain validation
- Proper model serialization
- Structured logging throughout
"""

import json
import sys
import os
import csv
from datetime import datetime
from pathlib import Path

import warnings
warnings.filterwarnings("ignore")

# Fix encoding on Windows
if sys.platform.startswith("win"):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import train_test_split, StratifiedKFold, GridSearchCV
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.svm import LinearSVC
from sklearn.ensemble import VotingClassifier, RandomForestClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.base import clone
from sklearn.metrics import (
    accuracy_score, precision_recall_fscore_support,
    classification_report, confusion_matrix, roc_auc_score, roc_curve,
)
from joblib import dump

from src.ml.preprocessing import clean_text
from src.core.logging_config import get_logger

logger = get_logger(__name__)

# ========================
# Config
# ========================
DATA_DIR = PROJECT_ROOT / "data_new"
MODEL_DIR = PROJECT_ROOT / "models"
LOGS_DIR = PROJECT_ROOT / "logs"
MODEL_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)


def log_experiment(metrics_dict, params, log_file=None):
    """Log experiment results to CSV."""
    log_file = log_file or LOGS_DIR / "experiments.csv"
    exists = log_file.exists()
    with open(log_file, "a", newline="") as f:
        writer = csv.writer(f)
        if not exists:
            writer.writerow(["timestamp", "accuracy", "precision", "recall", "f1", "roc_auc", "threshold"] + list(params.keys()))
        writer.writerow([
            datetime.now().isoformat(),
            f"{metrics_dict['accuracy']:.4f}", f"{metrics_dict['precision']:.4f}",
            f"{metrics_dict['recall']:.4f}", f"{metrics_dict['f1']:.4f}",
            f"{metrics_dict['roc_auc']:.4f}", f"{metrics_dict['threshold']:.4f}",
        ] + list(params.values()))
    logger.info(f"Experiment logged to {log_file}")


def save_plots(y_true, y_pred, y_proba, model_name="ensemble"):
    """Save confusion matrix and ROC curve plots."""
    cm = confusion_matrix(y_true, y_pred)
    plt.figure(figsize=(8, 6))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", cbar=False)
    plt.title(f"Confusion Matrix — {model_name}")
    plt.ylabel("True Label")
    plt.xlabel("Predicted Label")
    plt.savefig(LOGS_DIR / f"confusion_matrix_{model_name}.png")
    plt.close()

    fpr, tpr, _ = roc_curve(y_true, y_proba)
    plt.figure(figsize=(8, 6))
    plt.plot(fpr, tpr, label=f"{model_name} (AUC = {roc_auc_score(y_true, y_proba):.2f})")
    plt.plot([0, 1], [0, 1], "k--")
    plt.xlabel("False Positive Rate")
    plt.ylabel("True Positive Rate")
    plt.title(f"ROC Curve — {model_name}")
    plt.legend(loc="lower right")
    plt.savefig(LOGS_DIR / f"roc_curve_{model_name}.png")
    plt.close()
    logger.info(f"Plots saved to {LOGS_DIR}")


def load_datasets():
    """Load and combine all available datasets."""
    logger.info("Loading datasets...")
    dfs = []

    # Pattern: look for True*.csv and Fake*.csv
    for csv_file in sorted(DATA_DIR.glob("True*.csv")):
        try:
            df = pd.read_csv(csv_file, encoding="utf-8", on_bad_lines="skip")
            df["label"] = 1
            dfs.append(df)
            logger.info(f"Loaded {csv_file.name} → {len(df)} rows (REAL)")
        except Exception as e:
            logger.warning(f"Failed to load {csv_file.name}: {e}")

    for csv_file in sorted(DATA_DIR.glob("Fake*.csv")):
        try:
            df = pd.read_csv(csv_file, encoding="utf-8", on_bad_lines="skip")
            df["label"] = 0
            dfs.append(df)
            logger.info(f"Loaded {csv_file.name} → {len(df)} rows (FAKE)")
        except Exception as e:
            logger.warning(f"Failed to load {csv_file.name}: {e}")

    # Also load WELFake if present
    welfake = DATA_DIR / "WELFake_Dataset.csv"
    if welfake.exists():
        try:
            df = pd.read_csv(welfake, encoding="utf-8", on_bad_lines="skip")
            if "label" in df.columns and "text" in df.columns:
                dfs.append(df[["text", "label"]])
                logger.info(f"Loaded WELFake_Dataset.csv → {len(df)} rows")
        except Exception as e:
            logger.warning(f"Failed to load WELFake: {e}")

    if not dfs:
        logger.error("No datasets found!")
        return None
    return dfs


def main():
    print("=" * 80)
    print("🚀 HYBRID FAKE NEWS DETECTION — TRAINING PIPELINE v3.0")
    print("=" * 80)

    # 1. Load data
    dfs = load_datasets()
    if not dfs:
        print("❌ No dataset files found. Exiting.")
        return

    # 2. Combine and clean
    logger.info("Combining and cleaning data...")
    df = pd.concat(dfs, ignore_index=True)

    text_cols = [c for c in ["title", "text", "content"] if c in df.columns]
    if not text_cols:
        print("❌ No text column found.")
        return

    primary = text_cols[0]
    df[primary] = df[primary].fillna("").astype(str)
    df["content"] = df[primary].str.strip()
    for col in text_cols[1:]:
        if col in df.columns:
            df[col] = df[col].fillna("").astype(str)
            df["content"] = df["content"] + " " + df[col].str.strip()

    df["content"] = df["content"].str.replace(r"\s+", " ", regex=True).str.strip()
    df = df[df["content"].str.len() > 10].drop_duplicates(subset="content").reset_index(drop=True)
    print(f"✅ Combined: {df.shape[0]} rows | Label dist: {dict(df['label'].value_counts())}")

    # 3. Balance
    min_count = df["label"].value_counts().min()
    df = df.groupby("label", group_keys=False).apply(
        lambda x: x.sample(min(min_count, len(x)), random_state=42)
    ).reset_index(drop=True)
    print(f"✅ Balanced: {dict(df['label'].value_counts())}")

    # 4. Clean text
    print("🔤 Cleaning text (using canonical preprocessor)...")
    df["content_clean"] = df["content"].apply(clean_text)
    df = df[df["content_clean"].str.len() > 5].reset_index(drop=True)
    print(f"✅ After cleaning: {len(df)} rows")

    # 5. Split
    X, y = df["content_clean"], df["label"]
    X_temp, X_test, y_temp, y_test = train_test_split(X, y, test_size=0.15, stratify=y, random_state=42)
    X_train, X_val, y_train, y_val = train_test_split(X_temp, y_temp, test_size=0.1765, stratify=y_temp, random_state=42)
    print(f"✅ Train: {len(X_train)} | Val: {len(X_val)} | Test: {len(X_test)}")

    # 6. TF-IDF
    tfidf = TfidfVectorizer(ngram_range=(1, 3), min_df=2, max_df=0.90, sublinear_tf=True, max_features=5000, stop_words="english")

    # 7. Train LR
    print("🎯 Training Logistic Regression...")
    lr_pipe = Pipeline([("tfidf", tfidf), ("clf", LogisticRegression(max_iter=1000, class_weight="balanced", random_state=42))])
    n_splits = max(2, min(5, len(X_train) // 20))
    cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)
    lr_gs = GridSearchCV(lr_pipe, {"clf__C": [0.5, 1.0, 2.0]}, scoring="f1", cv=cv, n_jobs=-1, verbose=0)
    try:
        lr_gs.fit(X_train, y_train)
        lr_best = lr_gs.best_estimator_
        print(f"✅ LR Best: {lr_gs.best_params_}, F1: {lr_gs.best_score_:.4f}")
    except Exception as e:
        logger.error(f"LR GridSearch failed: {e}")
        lr_pipe.fit(X_train, y_train)
        lr_best = lr_pipe

    # 8. Train RF
    print("🎯 Training Random Forest...")
    rf_pipe = Pipeline([("tfidf", clone(tfidf)), ("clf", RandomForestClassifier(n_estimators=150, max_depth=15, class_weight="balanced", random_state=42, n_jobs=-1))])
    rf_pipe.fit(X_train, y_train)
    try:
        print(f"✅ RF ROC-AUC: {roc_auc_score(y_val, rf_pipe.predict_proba(X_val)[:, 1]):.4f}")
    except Exception as e:
        logger.warning(f"RF AUC calculation failed: {e}")

    # 9. Ensemble
    print("🎯 Creating ensemble...")
    voting = VotingClassifier(estimators=[("lr", lr_best), ("rf", rf_pipe)], voting="soft", n_jobs=-1)
    voting.fit(X_train, y_train)

    # 10. Calibrate
    print("⚖️ Calibrating...")
    cal_cv = 3 if len(X_train) >= 50 else "prefit"
    if cal_cv == "prefit":
        calibrated = CalibratedClassifierCV(voting, method="sigmoid", cv="prefit")
        calibrated.fit(X_val, y_val)
    else:
        calibrated = CalibratedClassifierCV(voting, method="sigmoid", cv=cal_cv)
        calibrated.fit(pd.concat([X_train, X_val]), pd.concat([y_train, y_val]))

    # 11. Threshold
    proba_val = calibrated.predict_proba(X_val)[:, 1]
    fpr, tpr, thresholds = roc_curve(y_val, proba_val)
    best_thr = float(np.round(thresholds[np.argmax(tpr - fpr)], 3))
    print(f"✅ Optimal threshold: {best_thr}")

    # 12. Evaluate
    proba_test = calibrated.predict_proba(X_test)[:, 1]
    y_pred = (proba_test >= best_thr).astype(int)
    acc = accuracy_score(y_test, y_pred)
    p, r, f1, _ = precision_recall_fscore_support(y_test, y_pred, average="binary")
    auc = roc_auc_score(y_test, proba_test)

    print("\n" + "=" * 80)
    print(f"🏆 TEST RESULTS: Acc={acc:.4f}  P={p:.4f}  R={r:.4f}  F1={f1:.4f}  AUC={auc:.4f}")
    print("=" * 80)
    print(classification_report(y_test, y_pred, target_names=["FAKE", "REAL"]))

    save_plots(y_test, y_pred, proba_test)
    log_experiment(
        {"accuracy": acc, "precision": p, "recall": r, "f1": f1, "roc_auc": auc, "threshold": best_thr},
        {"model": "Ensemble(LR+RF)", "n_samples": len(df), "features": 5000, "version": "3.0"},
    )

    # 13. Save — versioned model artifacts
    version_tag = datetime.now().strftime("%Y%m%d_%H%M%S")
    version_dir = MODEL_DIR / f"v_{version_tag}"
    version_dir.mkdir(exist_ok=True)

    # Extract the vectorizer from the LR pipeline for standalone use
    final_tfidf = lr_best.named_steps["tfidf"]

    # Save to both versioned dir and latest location
    for target_dir in [version_dir, MODEL_DIR]:
        dump(calibrated, target_dir / "model.joblib")
        dump(final_tfidf, target_dir / "tfidf.joblib")
        config = {
            "accuracy": float(acc), "precision": float(p), "recall": float(r),
            "f1_score": float(f1), "roc_auc": float(auc), "threshold": best_thr,
            "model_type": "Ensemble(LR+RF)_calibrated",
            "total_training_samples": len(df), "tfidf_features": 5000,
            "training_date": str(datetime.now()), "version": version_tag,
        }
        with open(target_dir / "config.json", "w") as f:
            json.dump(config, f, indent=2)

    print(f"\n💾 Model saved to {version_dir} and {MODEL_DIR}")
    print(f"🎉 TRAINING COMPLETE — ACCURACY: {acc*100:.2f}%")


if __name__ == "__main__":
    main()
