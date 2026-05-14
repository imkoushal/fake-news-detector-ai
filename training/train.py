"""
Hybrid Fake News Detector — Training Pipeline v4.0

Phase 1 Improvements:
- Consolidated data pipeline: loads from data_new/ (100K+ real articles)
- LIAR dataset integration (12K+ graded political claims, binarized)
- WELFake dataset integration (72K articles)
- Near-deduplication across all sources
- Fixed train/serve skew: saves model.joblib + tfidf.joblib correctly
- Fixed data leakage: calibration uses only training data
- Structured logging throughout
"""

import json
import sys
import os
import csv
from datetime import datetime
from pathlib import Path
from hashlib import md5

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
DATA_DIR_FALLBACK = PROJECT_ROOT / "data"
LIAR_DIR = DATA_DIR / "liar"
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


# ========================
# Phase 1: Data Loading Functions
# ========================

def load_csv_datasets(data_dir: Path):
    """Load True*.csv and Fake*.csv files from a directory."""
    dfs = []
    for csv_file in sorted(data_dir.glob("True*.csv")):
        try:
            df = pd.read_csv(csv_file, encoding="utf-8", on_bad_lines="skip")
            df["label"] = 1
            df["source_dataset"] = csv_file.name
            dfs.append(df)
            logger.info(f"Loaded {csv_file.name} → {len(df):,} rows (REAL)")
        except Exception as e:
            logger.warning(f"Failed to load {csv_file.name}: {e}")

    for csv_file in sorted(data_dir.glob("Fake*.csv")):
        try:
            df = pd.read_csv(csv_file, encoding="utf-8", on_bad_lines="skip")
            df["label"] = 0
            df["source_dataset"] = csv_file.name
            dfs.append(df)
            logger.info(f"Loaded {csv_file.name} → {len(df):,} rows (FAKE)")
        except Exception as e:
            logger.warning(f"Failed to load {csv_file.name}: {e}")
    return dfs


def load_welfake_dataset(data_dir: Path):
    """Load the WELFake dataset (72K articles, pre-labeled)."""
    welfake_path = data_dir / "WELFake_Dataset.csv"
    if not welfake_path.exists():
        return None
    try:
        df = pd.read_csv(welfake_path, encoding="utf-8", on_bad_lines="skip")
        if "label" in df.columns and "text" in df.columns:
            # WELFake: 0 = reliable (real), 1 = unreliable (fake) → invert to our convention
            df["label"] = df["label"].map({0: 1, 1: 0})
            df["source_dataset"] = "WELFake"
            df = df.dropna(subset=["label"])
            df["label"] = df["label"].astype(int)
            logger.info(f"Loaded WELFake_Dataset.csv → {len(df):,} rows")
            return df[["text", "label", "source_dataset"]]
    except Exception as e:
        logger.warning(f"Failed to load WELFake: {e}")
    return None


def load_liar_dataset(liar_dir: Path):
    """Load and binarize the LIAR benchmark dataset."""
    if not liar_dir.exists():
        return None

    FAKE_LABELS = {"pants-fire", "false", "barely-true"}
    REAL_LABELS = {"true", "mostly-true"}

    dfs = []
    for tsv_name in ["train.tsv", "valid.tsv", "test.tsv"]:
        tsv_path = liar_dir / tsv_name
        if not tsv_path.exists():
            continue
        try:
            df = pd.read_csv(tsv_path, sep="\t", header=None, usecols=[1, 2],
                           names=["raw_label", "text"], on_bad_lines="skip")
            df = df[df["raw_label"].isin(FAKE_LABELS | REAL_LABELS)].copy()
            df["label"] = df["raw_label"].apply(lambda x: 0 if x in FAKE_LABELS else 1)
            df["source_dataset"] = f"LIAR_{tsv_name}"
            dfs.append(df[["text", "label", "source_dataset"]])
            logger.info(f"Loaded LIAR/{tsv_name} → {len(df):,} rows")
        except Exception as e:
            logger.warning(f"Failed to load LIAR/{tsv_name}: {e}")

    if not dfs:
        return None
    return pd.concat(dfs, ignore_index=True)


def load_generic_csv(data_dir: Path):
    """Load data.csv if it exists (URLs, Headline, Body, Label format)."""
    data_csv = data_dir / "data.csv"
    if not data_csv.exists():
        return None
    try:
        df = pd.read_csv(data_csv, encoding="utf-8", on_bad_lines="skip")
        if "Label" in df.columns:
            text_col = "Body" if "Body" in df.columns else "Headline" if "Headline" in df.columns else None
            if text_col:
                df = df[[text_col, "Label"]].copy()
                df.columns = ["text", "label"]
                if df["label"].dtype == object:
                    label_map = {"fake": 0, "false": 0, "real": 1, "true": 1, "1": 1, "0": 0}
                    df["label"] = df["label"].str.lower().str.strip().map(label_map)
                    df = df.dropna(subset=["label"])
                    df["label"] = df["label"].astype(int)
                df["source_dataset"] = "data.csv"
                logger.info(f"Loaded data.csv → {len(df):,} rows")
                return df[["text", "label", "source_dataset"]]
    except Exception as e:
        logger.warning(f"Failed to load data.csv: {e}")
    return None


def near_dedup(df, col="content"):
    """Remove near-duplicate articles using content fingerprinting."""
    original_len = len(df)
    def fingerprint(text):
        text = str(text).strip().lower()
        snippet = text[:200] + text[-200:] if len(text) > 400 else text
        return md5(snippet.encode("utf-8", errors="ignore")).hexdigest()
    df["_fingerprint"] = df[col].apply(fingerprint)
    df = df.drop_duplicates(subset="_fingerprint").drop(columns=["_fingerprint"])
    df = df.reset_index(drop=True)
    removed = original_len - len(df)
    if removed > 0:
        logger.info(f"Near-dedup removed {removed:,} duplicates ({original_len:,} → {len(df):,})")
    return df


def main():
    print("=" * 80)
    print("🚀 HYBRID FAKE NEWS DETECTION — TRAINING PIPELINE v4.0")
    print("   Phase 1: Consolidated Data Pipeline + Train/Serve Fix")
    print("=" * 80)

    # 1. Load ALL data sources
    print("\n📂 Loading datasets from all sources...")
    all_dfs = []

    print(f"\n  📁 Source: {DATA_DIR}/")
    csv_dfs = load_csv_datasets(DATA_DIR)
    if csv_dfs:
        all_dfs.extend(csv_dfs)

    if DATA_DIR_FALLBACK.exists() and DATA_DIR_FALLBACK != DATA_DIR:
        print(f"\n  📁 Source: {DATA_DIR_FALLBACK}/ (fallback)")
        fallback_dfs = load_csv_datasets(DATA_DIR_FALLBACK)
        if fallback_dfs:
            all_dfs.extend(fallback_dfs)

    print(f"\n  📁 Source: WELFake")
    welfake_df = load_welfake_dataset(DATA_DIR)
    if welfake_df is not None:
        all_dfs.append(welfake_df)

    print(f"\n  📁 Source: LIAR Benchmark")
    liar_df = load_liar_dataset(LIAR_DIR)
    if liar_df is not None:
        all_dfs.append(liar_df)

    print(f"\n  📁 Source: data.csv")
    generic_df = load_generic_csv(DATA_DIR)
    if generic_df is not None:
        all_dfs.append(generic_df)

    if not all_dfs:
        print("❌ No datasets found. Exiting.")
        return

    # 2. Combine and clean
    logger.info("Combining and cleaning data...")
    df = pd.concat(all_dfs, ignore_index=True)

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
    print(f"✅ Combined: {df.shape[0]:,} rows | Label dist: {dict(df['label'].value_counts())}")

    # 3. Near-deduplication
    print("\n🔍 Running near-deduplication...")
    df = near_dedup(df, col="content")

    # 4. Balance
    min_count = df["label"].value_counts().min()
    balanced_parts = []
    for label_val in df["label"].unique():
        part = df[df["label"] == label_val].sample(min(min_count, len(df[df["label"] == label_val])), random_state=42)
        balanced_parts.append(part)
    df = pd.concat(balanced_parts, ignore_index=True)
    print(f"✅ Balanced: {dict(df['label'].value_counts())}")

    # 5. Clean text
    print("🔤 Cleaning text (using canonical preprocessor)...")
    df["content_clean"] = df["content"].apply(clean_text)
    df = df[df["content_clean"].str.len() > 5].reset_index(drop=True)
    print(f"✅ After cleaning: {len(df):,} rows")

    # 6. Split
    X, y = df["content_clean"], df["label"]
    X_temp, X_test, y_temp, y_test = train_test_split(X, y, test_size=0.15, stratify=y, random_state=42)
    X_train, X_val, y_train, y_val = train_test_split(X_temp, y_temp, test_size=0.1765, stratify=y_temp, random_state=42)
    print(f"✅ Train: {len(X_train):,} | Val: {len(X_val):,} | Test: {len(X_test):,}")

    # 7. TF-IDF
    tfidf = TfidfVectorizer(
        ngram_range=(1, 3), min_df=2, max_df=0.85,
        sublinear_tf=True, max_features=15000, stop_words="english"
    )

    # 8. Train LR
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

    # 9. Train RF
    print("🎯 Training Random Forest...")
    rf_pipe = Pipeline([("tfidf", clone(tfidf)), ("clf", RandomForestClassifier(n_estimators=150, max_depth=15, class_weight="balanced", random_state=42, n_jobs=-1))])
    rf_pipe.fit(X_train, y_train)
    try:
        print(f"✅ RF ROC-AUC: {roc_auc_score(y_val, rf_pipe.predict_proba(X_val)[:, 1]):.4f}")
    except Exception as e:
        logger.warning(f"RF AUC calculation failed: {e}")

    # 10. Ensemble
    print("🎯 Creating ensemble...")
    voting = VotingClassifier(estimators=[("lr", lr_best), ("rf", rf_pipe)], voting="soft", n_jobs=-1)
    voting.fit(X_train, y_train)

    # 11. Calibrate (FIXED: no data leakage)
    print("⚖️ Calibrating...")
    cal_cv = 5 if len(X_train) >= 100 else 3 if len(X_train) >= 50 else "prefit"
    if cal_cv == "prefit":
        calibrated = CalibratedClassifierCV(voting, method="sigmoid", cv="prefit")
        calibrated.fit(X_val, y_val)
    else:
        calibrated = CalibratedClassifierCV(voting, method="sigmoid", cv=cal_cv)
        calibrated.fit(X_train, y_train)  # FIX: Only train data

    # 12. Threshold
    proba_val = calibrated.predict_proba(X_val)[:, 1]
    fpr, tpr, thresholds = roc_curve(y_val, proba_val)
    best_thr = float(np.round(thresholds[np.argmax(tpr - fpr)], 3))
    print(f"✅ Optimal threshold: {best_thr}")

    # 13. Evaluate
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
        {"model": "Ensemble(LR+RF)", "n_samples": len(df), "features": 15000, "version": "4.0_phase1"},
    )

    # 14. Save (FIXED: proper train/serve alignment)
    version_tag = datetime.now().strftime("%Y%m%d_%H%M%S")
    version_dir = MODEL_DIR / f"v_{version_tag}"
    version_dir.mkdir(exist_ok=True)

    final_tfidf = lr_best.named_steps["tfidf"]

    config = {
        "accuracy": float(acc), "precision": float(p), "recall": float(r),
        "f1_score": float(f1), "roc_auc": float(auc), "threshold": best_thr,
        "model_type": "Ensemble(LR+RF)_calibrated",
        "total_training_samples": len(df), "tfidf_features": 15000,
        "training_date": str(datetime.now()), "version": version_tag,
        "datasets_used": list(df["source_dataset"].unique()) if "source_dataset" in df.columns else [],
    }

    for target_dir in [version_dir, MODEL_DIR]:
        dump(calibrated, target_dir / "model.joblib")
        dump(final_tfidf, target_dir / "tfidf.joblib")
        with open(target_dir / "config.json", "w") as f:
            json.dump(config, f, indent=2)

    print(f"\n💾 Model saved to {version_dir} and {MODEL_DIR}")
    print(f"🎉 TRAINING COMPLETE — ACCURACY: {acc*100:.2f}%")


if __name__ == "__main__":
    main()
