"""
Hybrid Fake News Detector - Model Training Pipeline v4.3

Phase 1: Consolidated data pipeline (100K+ articles), LIAR + WELFake integration,
         near-deduplication, fixed train/serve skew & data leakage.
Phase 2: 20 handcrafted meta-features hstacked with TF-IDF.
Phase 3: 5-model StackingClassifier (LR, RF, SGD, LinearSVC, LightGBM)
         replaces 2-model VotingClassifier for learned model combination.
Phase 4: RandomizedSearchCV for LR + LightGBM hyperparameter tuning,
         cross-domain validation (separate script).
"""

import os
import json
import sys
from pathlib import Path
import warnings
import csv
from datetime import datetime
from hashlib import md5
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

warnings.filterwarnings("ignore")

# Fix encoding issues on Windows (line_buffering=True so output appears immediately)
if sys.platform.startswith('win'):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', line_buffering=True)

import numpy as np
import pandas as pd
import scipy.sparse as sp
from sklearn.model_selection import train_test_split, StratifiedKFold, GridSearchCV, RandomizedSearchCV
from scipy.stats import loguniform, randint
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression, SGDClassifier
from sklearn.svm import LinearSVC
from sklearn.ensemble import StackingClassifier, RandomForestClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.base import clone, BaseEstimator, ClassifierMixin
from sklearn.metrics import (
    accuracy_score, precision_recall_fscore_support,
    classification_report, confusion_matrix, roc_auc_score, roc_curve
)
from joblib import dump
import lightgbm as lgb
from meta_features import extract_batch, N_META_FEATURES, FEATURE_NAMES

# Import unified cleaner and advanced features
try:
    from utils import clean_text
except ImportError:
    # Fallback if running from a different directory
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from utils import clean_text

# ========================
# Config / Paths
# ========================
DATA_DIR = Path("data_new")       # Primary: large datasets (100K+ articles)
DATA_DIR_FALLBACK = Path("data")  # Fallback: small placeholder data
LIAR_DIR = DATA_DIR / "liar"      # LIAR benchmark dataset
MODEL_DIR = Path("models")
LOGS_DIR = Path("logs")
MODEL_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)


def log_experiment(metrics, params, log_file=LOGS_DIR / "experiments.csv"):
    """Log experiment results to CSV"""
    file_exists = log_file.exists()
    
    with open(log_file, 'a', newline='') as f:
        writer = csv.writer(f)
        if not file_exists:
            header = ['timestamp', 'accuracy', 'precision', 'recall', 'f1', 'roc_auc', 'threshold'] + list(params.keys())
            writer.writerow(header)
        
        row = [
            datetime.now().isoformat(),
            f"{metrics['accuracy']:.4f}",
            f"{metrics['precision']:.4f}",
            f"{metrics['recall']:.4f}",
            f"{metrics['f1']:.4f}",
            f"{metrics['roc_auc']:.4f}",
            f"{metrics['threshold']:.4f}"
        ] + list(params.values())
        writer.writerow(row)
    print(f"📝 Experiment logged to {log_file}")

def save_plots(y_true, y_pred, y_proba, model_name="ensemble"):
    """Save confusion matrix and ROC curve plots"""
    # Confusion Matrix
    cm = confusion_matrix(y_true, y_pred)
    plt.figure(figsize=(8, 6))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', cbar=False)
    plt.title(f'Confusion Matrix - {model_name}')
    plt.ylabel('True Label')
    plt.xlabel('Predicted Label')
    plt.savefig(LOGS_DIR / f"confusion_matrix_{model_name}.png")
    plt.close()
    
    # ROC Curve
    fpr, tpr, _ = roc_curve(y_true, y_proba)
    plt.figure(figsize=(8, 6))
    plt.plot(fpr, tpr, label=f'{model_name} (AUC = {roc_auc_score(y_true, y_proba):.2f})')
    plt.plot([0, 1], [0, 1], 'k--')
    plt.xlabel('False Positive Rate')
    plt.ylabel('True Positive Rate')
    plt.title(f'ROC Curve - {model_name}')
    plt.legend(loc='lower right')
    plt.savefig(LOGS_DIR / f"roc_curve_{model_name}.png")
    plt.close()
    print(f"📊 Plots saved to {LOGS_DIR}")


# ========================
# Phase 1: Data Loading Functions
# ========================

def load_csv_datasets(data_dir: Path):
    """Load True*.csv and Fake*.csv files from a directory."""
    dfs = []

    # Load all true news files
    for csv_file in sorted(data_dir.glob("True*.csv")):
        try:
            df = pd.read_csv(csv_file, encoding="utf-8", on_bad_lines="skip")
            df["label"] = 1  # REAL
            df["source_dataset"] = csv_file.name
            dfs.append(df)
            print(f"  ✅ Loaded {csv_file.name} → {len(df):,} rows (REAL)")
        except Exception as e:
            print(f"  ⚠️  Failed to load {csv_file.name}: {e}")

    # Load all fake news files
    for csv_file in sorted(data_dir.glob("Fake*.csv")):
        try:
            df = pd.read_csv(csv_file, encoding="utf-8", on_bad_lines="skip")
            df["label"] = 0  # FAKE
            df["source_dataset"] = csv_file.name
            dfs.append(df)
            print(f"  ✅ Loaded {csv_file.name} → {len(df):,} rows (FAKE)")
        except Exception as e:
            print(f"  ⚠️  Failed to load {csv_file.name}: {e}")

    return dfs


def load_welfake_dataset(data_dir: Path):
    """Load the WELFake dataset (72K articles, pre-labeled)."""
    welfake_path = data_dir / "WELFake_Dataset.csv"
    if not welfake_path.exists():
        print(f"  ⚠️  WELFake_Dataset.csv not found in {data_dir}")
        return None
    
    try:
        df = pd.read_csv(welfake_path, encoding="utf-8", on_bad_lines="skip")
        if "label" in df.columns and "text" in df.columns:
            # WELFake uses label=1 for fake, label=0 for real — INVERT to match our convention
            # Our convention: label=1 → REAL, label=0 → FAKE
            # Check the WELFake convention by inspecting data
            # WELFake: 0 = reliable (real), 1 = unreliable (fake)
            df["label"] = df["label"].map({0: 1, 1: 0})  # Invert: 0(real)→1, 1(fake)→0
            df["source_dataset"] = "WELFake"
            # Drop rows where label mapping failed (NaN)
            df = df.dropna(subset=["label"])
            df["label"] = df["label"].astype(int)
            print(f"  ✅ Loaded WELFake_Dataset.csv → {len(df):,} rows")
            return df[["text", "label", "source_dataset"]]
        else:
            print(f"  ⚠️  WELFake missing required columns (need 'text' and 'label')")
            return None
    except Exception as e:
        print(f"  ⚠️  Failed to load WELFake: {e}")
        return None


def load_liar_dataset(liar_dir: Path):
    """
    Load and binarize the LIAR benchmark dataset.
    
    LIAR has 6-way labels: pants-fire, false, barely-true, half-true, mostly-true, true
    We map to binary:
      FAKE (0): pants-fire, false, barely-true
      REAL (1): mostly-true, true
      SKIP: half-true (too ambiguous for binary classification)
    """
    if not liar_dir.exists():
        print(f"  ⚠️  LIAR directory not found: {liar_dir}")
        return None

    FAKE_LABELS = {"pants-fire", "false", "barely-true"}
    REAL_LABELS = {"true", "mostly-true"}
    # "half-true" is intentionally skipped — too ambiguous

    dfs = []
    for tsv_name in ["train.tsv", "valid.tsv", "test.tsv"]:
        tsv_path = liar_dir / tsv_name
        if not tsv_path.exists():
            continue
        try:
            df = pd.read_csv(
                tsv_path, sep="\t", header=None,
                usecols=[1, 2],
                names=["raw_label", "text"],
                on_bad_lines="skip"
            )
            # Keep only clearly fake or clearly real
            df = df[df["raw_label"].isin(FAKE_LABELS | REAL_LABELS)].copy()
            df["label"] = df["raw_label"].apply(lambda x: 0 if x in FAKE_LABELS else 1)
            df["source_dataset"] = f"LIAR_{tsv_name}"
            dfs.append(df[["text", "label", "source_dataset"]])
            print(f"  ✅ Loaded LIAR/{tsv_name} → {len(df):,} rows "
                  f"(Fake: {(df['label']==0).sum()}, Real: {(df['label']==1).sum()}, "
                  f"Skipped half-true)")
        except Exception as e:
            print(f"  ⚠️  Failed to load LIAR/{tsv_name}: {e}")

    if not dfs:
        return None
    
    combined = pd.concat(dfs, ignore_index=True)
    print(f"  ✅ LIAR total: {len(combined):,} rows")
    return combined


def load_generic_csv(data_dir: Path):
    """Load data.csv if it exists (URLs, Headline, Body, Label format)."""
    data_csv = data_dir / "data.csv"
    if not data_csv.exists():
        return None
    
    try:
        df = pd.read_csv(data_csv, encoding="utf-8", on_bad_lines="skip")
        # Expected columns: URLs, Headline, Body, Label
        if "Label" in df.columns:
            text_col = "Body" if "Body" in df.columns else "Headline" if "Headline" in df.columns else None
            if text_col:
                df = df[[text_col, "Label"]].copy()
                df.columns = ["text", "label"]
                # Normalize labels: ensure 0=FAKE, 1=REAL
                if df["label"].dtype == object:
                    label_map = {"fake": 0, "false": 0, "real": 1, "true": 1, "1": 1, "0": 0}
                    df["label"] = df["label"].str.lower().str.strip().map(label_map)
                    df = df.dropna(subset=["label"])
                    df["label"] = df["label"].astype(int)
                df["source_dataset"] = "data.csv"
                print(f"  ✅ Loaded data.csv → {len(df):,} rows")
                return df[["text", "label", "source_dataset"]]
    except Exception as e:
        print(f"  ⚠️  Failed to load data.csv: {e}")
    return None


def near_dedup(df, col="content", verbose=True):
    """
    Remove near-duplicate articles using content fingerprinting.
    Uses a hash of the first 200 + last 200 characters to catch
    articles that differ only in headers/footers.
    """
    original_len = len(df)
    
    def fingerprint(text):
        text = str(text).strip().lower()
        # Use first 200 + last 200 chars as fingerprint
        snippet = text[:200] + text[-200:] if len(text) > 400 else text
        return md5(snippet.encode("utf-8", errors="ignore")).hexdigest()
    
    df["_fingerprint"] = df[col].apply(fingerprint)
    df = df.drop_duplicates(subset="_fingerprint").drop(columns=["_fingerprint"])
    df = df.reset_index(drop=True)
    
    removed = original_len - len(df)
    if verbose and removed > 0:
        print(f"  🧹 Near-dedup removed {removed:,} duplicates ({original_len:,} → {len(df):,})")
    
    return df


def main():
    print("=" * 80)
    print("🚀 HYBRID FAKE NEWS DETECTION - TRAINING PIPELINE v4.3")
    print("   Phase 4: RandomizedSearchCV + Cross-Domain Validation")
    print("=" * 80)

    # ========================
    # 1️⃣ Load ALL datasets
    # ========================
    print("\n📂 Loading datasets from all sources...")
    all_dfs = []
    total_sources = 0

    # Source 1: True/Fake CSVs from data_new/
    print(f"\n  📁 Source: {DATA_DIR}/")
    csv_dfs = load_csv_datasets(DATA_DIR)
    if csv_dfs:
        all_dfs.extend(csv_dfs)
        total_sources += len(csv_dfs)

    # Source 2: True/Fake CSVs from data/ (fallback)
    if DATA_DIR_FALLBACK.exists() and DATA_DIR_FALLBACK != DATA_DIR:
        print(f"\n  📁 Source: {DATA_DIR_FALLBACK}/ (fallback)")
        fallback_dfs = load_csv_datasets(DATA_DIR_FALLBACK)
        if fallback_dfs:
            all_dfs.extend(fallback_dfs)
            total_sources += len(fallback_dfs)

    # Source 3: WELFake dataset
    print(f"\n  📁 Source: WELFake")
    welfake_df = load_welfake_dataset(DATA_DIR)
    if welfake_df is not None:
        all_dfs.append(welfake_df)
        total_sources += 1

    # Source 4: LIAR benchmark dataset
    print(f"\n  📁 Source: LIAR Benchmark")
    liar_df = load_liar_dataset(LIAR_DIR)
    if liar_df is not None:
        all_dfs.append(liar_df)
        total_sources += 1

    # Source 5: data.csv (generic format)
    print(f"\n  📁 Source: data.csv")
    generic_df = load_generic_csv(DATA_DIR)
    if generic_df is not None:
        all_dfs.append(generic_df)
        total_sources += 1

    if not all_dfs:
        print("❌ No dataset files found. Please add CSV files to 'data_new/' or 'data/'.")
        return

    print(f"\n✅ Loaded {total_sources} dataset source(s)")

    # ========================
    # 2️⃣ Combine and clean
    # ========================
    print("\n🧹 Combining and cleaning data...")
    df = pd.concat(all_dfs, ignore_index=True)

    # Identify text column — different datasets use different column names
    text_cols = [col for col in ["title", "text", "content"] if col in df.columns]
    if not text_cols:
        print("❌ No text column found. Expected 'title', 'text', or 'content'")
        return

    primary_col = text_cols[0]
    df[primary_col] = df[primary_col].fillna("").astype(str)
    df["content"] = df[primary_col].str.strip()

    # Handle multiple text columns — concatenate title + text for richer signal
    for col in text_cols[1:]:
        if col in df.columns:
            df[col] = df[col].fillna("").astype(str)
            df["content"] = df["content"] + " " + df[col].str.strip()

    df["content"] = df["content"].str.replace(r"\s+", " ", regex=True).str.strip()
    
    # Remove very short texts and exact duplicates
    df = df[df["content"].str.len() > 10].drop_duplicates(subset="content").reset_index(drop=True)

    print(f"✅ Combined dataset shape: {df.shape}")
    print(f"📊 Label distribution:\n{df['label'].value_counts()}")

    # Show dataset source breakdown
    if "source_dataset" in df.columns:
        print(f"\n📊 Source breakdown:")
        for src, count in df["source_dataset"].value_counts().items():
            print(f"   {src}: {count:,} rows")

    # ========================
    # 3️⃣ Near-deduplication (Phase 1 improvement)
    # ========================
    print("\n🔍 Running near-deduplication...")
    df = near_dedup(df, col="content")

    # ========================
    # 4️⃣ Balance dataset
    # ========================
    print("\n⚖️  Balancing dataset...")
    min_count = df["label"].value_counts().min()
    balanced_parts = []
    for label_val in df["label"].unique():
        part = df[df["label"] == label_val].sample(min(min_count, len(df[df["label"] == label_val])), random_state=42)
        balanced_parts.append(part)
    df = pd.concat(balanced_parts, ignore_index=True)
    print(f"✅ Balanced: {dict(df['label'].value_counts())}")

    # ========================
    # 5️⃣ Clean text (with progress reporting)
    # ========================
    print("\n🔤 Cleaning text...")
    # Use a smaller sample for quick testing if needed, or full dataset
    # df = df.sample(min(1000, len(df))) # Uncomment for quick debug
    total = len(df)
    batch_size = max(1, total // 20)  # Report every 5%
    cleaned = []
    for i, text in enumerate(df["content"]):
        cleaned.append(clean_text(text))
        if (i + 1) % batch_size == 0 or (i + 1) == total:
            pct = (i + 1) / total * 100
            print(f"  🔄 Cleaning: {i+1:,}/{total:,} ({pct:.0f}%)", flush=True)
    df["content_clean"] = cleaned
    df = df[df["content_clean"].str.len() > 5].reset_index(drop=True)
    print(f"✅ Dataset after cleaning: {len(df):,} rows")

    # ========================
    # 5.5️⃣ Extract meta features from RAW text (Phase 2)
    # ========================
    # Meta features capture signals that clean_text destroys: caps, punctuation,
    # conspiracy language, sensationalism, readability, etc.
    print("\n🧬 Extracting meta features from raw text...")
    import time as _time
    _t0 = _time.time()
    meta_all = extract_batch(df["content"].values)
    print(f"✅ Extracted {N_META_FEATURES} meta features for {len(df):,} rows ({_time.time()-_t0:.1f}s)")
    print(f"   Features: {', '.join(FEATURE_NAMES[:5])}... +{N_META_FEATURES-5} more")

    # ========================
    # 6️⃣ Split data (train / val / test)
    # ========================
    print("\n✂️  Splitting data...")
    X_text = df["content_clean"]
    y = df["label"]
    indices = np.arange(len(df))

    idx_temp, idx_test, y_temp, y_test = train_test_split(
        indices, y, test_size=0.15, stratify=y, random_state=42
    )
    idx_train, idx_val, y_train, y_val = train_test_split(
        idx_temp, y_temp, test_size=0.1765, stratify=y_temp, random_state=42
    )

    X_train = X_text.iloc[idx_train]
    X_val = X_text.iloc[idx_val]
    X_test = X_text.iloc[idx_test]

    meta_train = meta_all[idx_train]
    meta_val = meta_all[idx_val]
    meta_test = meta_all[idx_test]

    print(f"✅ Train: {len(X_train):,}, Val: {len(X_val):,}, Test: {len(X_test):,}")

    # ========================
    # 7️⃣ Build TF-IDF + Meta Features (fit ONCE upfront for speed)
    # ========================
    import time
    t_start = time.time()
    print("\n📝 Building TF-IDF vectorizer...")
    tfidf = TfidfVectorizer(
        ngram_range=(1, 3),
        min_df=2,
        max_df=0.85,         # Tighter filter on ubiquitous terms (was 0.90)
        sublinear_tf=True,
        max_features=15000,  # More discriminative features (was 5000)
        stop_words="english"
    )

    # FIT TF-IDF ONCE on training data, then transform all splits
    X_train_tfidf_raw = tfidf.fit_transform(X_train)
    X_val_tfidf_raw = tfidf.transform(X_val)
    X_test_tfidf_raw = tfidf.transform(X_test)
    print(f"✅ TF-IDF fitted: {X_train_tfidf_raw.shape[1]:,} features ({time.time()-t_start:.1f}s)")

    # ========================
    # 7.5️⃣ Scale meta features and combine with TF-IDF (Phase 2)
    # ========================
    print("\n🧬 Combining TF-IDF + meta features...")
    scaler = StandardScaler()
    meta_train_scaled = scaler.fit_transform(meta_train)
    meta_val_scaled = scaler.transform(meta_val)
    meta_test_scaled = scaler.transform(meta_test)

    # hstack sparse TF-IDF + dense meta features → sparse combined matrix
    X_train_tfidf = sp.hstack([X_train_tfidf_raw, sp.csr_matrix(meta_train_scaled)], format="csr")
    X_val_tfidf = sp.hstack([X_val_tfidf_raw, sp.csr_matrix(meta_val_scaled)], format="csr")
    X_test_tfidf = sp.hstack([X_test_tfidf_raw, sp.csr_matrix(meta_test_scaled)], format="csr")
    print(f"✅ Combined feature matrix: {X_train_tfidf.shape[1]:,} features "
          f"({X_train_tfidf_raw.shape[1]} TF-IDF + {N_META_FEATURES} meta)")

    # ========================
    # 8️⃣ Train 5 base models (Phase 3)
    # ========================
    cv = StratifiedKFold(n_splits=3, shuffle=True, random_state=42)

    def eval_model(name, clf, X_tr, y_tr, X_v, y_v, t0):
        """Evaluate a single model on validation set."""
        try:
            auc = roc_auc_score(y_v, clf.predict_proba(X_v)[:, 1])
            f1 = precision_recall_fscore_support(y_v, clf.predict(X_v), average="binary")[2]
            print(f"  ✅ {name}: F1={f1:.4f}, AUC={auc:.4f} ({time.time()-t0:.1f}s)")
        except Exception as e:
            print(f"  ⚠️ {name} eval error: {e}")

    # --- Model 1: Logistic Regression (with RandomizedSearchCV) ---
    print("\n🎯 [1/5] Training Logistic Regression (RandomizedSearchCV)...")
    t0 = time.time()
    lr_clf = LogisticRegression(max_iter=2000, class_weight="balanced", random_state=42)
    lr_param_dist = {
        "C": loguniform(0.01, 100),
        "solver": ["lbfgs", "liblinear", "saga"],
        "penalty": ["l2"],
    }
    lr_rs = RandomizedSearchCV(
        lr_clf, lr_param_dist,
        n_iter=20, scoring="f1", cv=cv, n_jobs=-1,
        random_state=42, verbose=0,
    )
    try:
        lr_rs.fit(X_train_tfidf, y_train)
        lr_best = lr_rs.best_estimator_
        print(f"  Best params: C={lr_rs.best_params_['C']:.4f}, "
              f"solver={lr_rs.best_params_['solver']}, CV-F1={lr_rs.best_score_:.4f}")
    except Exception as e:
        print(f"  ⚠️ RandomizedSearch failed ({e}), fitting default")
        lr_clf.fit(X_train_tfidf, y_train)
        lr_best = lr_clf
    eval_model("LR", lr_best, X_train_tfidf, y_train, X_val_tfidf, y_val, t0)

    # --- Model 2: Random Forest ---
    print("\n🎯 [2/5] Training Random Forest...")
    t0 = time.time()
    rf_clf = RandomForestClassifier(
        n_estimators=100, max_depth=15, class_weight="balanced",
        random_state=42, n_jobs=-1
    )
    rf_clf.fit(X_train_tfidf, y_train)
    eval_model("RF", rf_clf, X_train_tfidf, y_train, X_val_tfidf, y_val, t0)

    # --- Model 3: SGD (modified_huber gives probabilities) ---
    print("\n🎯 [3/5] Training SGD Classifier...")
    t0 = time.time()
    sgd_clf = SGDClassifier(
        loss="modified_huber", max_iter=1000, class_weight="balanced",
        random_state=42, n_jobs=-1
    )
    sgd_clf.fit(X_train_tfidf, y_train)
    eval_model("SGD", sgd_clf, X_train_tfidf, y_train, X_val_tfidf, y_val, t0)

    # --- Model 4: LinearSVC (calibrated for probabilities) ---
    print("\n🎯 [4/5] Training LinearSVC (calibrated)...")
    t0 = time.time()
    svc_base = LinearSVC(max_iter=2000, class_weight="balanced", random_state=42)
    svc_clf = CalibratedClassifierCV(svc_base, cv=3, method="sigmoid")
    svc_clf.fit(X_train_tfidf, y_train)
    eval_model("SVC", svc_clf, X_train_tfidf, y_train, X_val_tfidf, y_val, t0)

    # --- Model 5: LightGBM (with RandomizedSearchCV) ---
    print("\n🎯 [5/5] Training LightGBM (RandomizedSearchCV)...")
    t0 = time.time()
    lgbm_base = lgb.LGBMClassifier(
        class_weight="balanced", random_state=42, n_jobs=-1, verbose=-1
    )
    lgbm_param_dist = {
        "n_estimators": [100, 200, 300, 400],
        "max_depth": [6, 8, 10, 12, -1],
        "learning_rate": [0.05, 0.1, 0.15, 0.2],
        "num_leaves": [31, 50, 80, 127],
        "min_child_samples": [10, 20, 50],
        "subsample": [0.7, 0.8, 0.9, 1.0],
    }
    lgbm_rs = RandomizedSearchCV(
        lgbm_base, lgbm_param_dist,
        n_iter=10, scoring="f1", cv=cv, n_jobs=1,  # n_jobs=1 to avoid LightGBM parallel crash on Windows
        random_state=42, verbose=0,
    )
    try:
        lgbm_rs.fit(X_train_tfidf, y_train)
        lgbm_clf = lgbm_rs.best_estimator_
        print(f"  Best params: n_est={lgbm_rs.best_params_['n_estimators']}, "
              f"depth={lgbm_rs.best_params_['max_depth']}, "
              f"lr={lgbm_rs.best_params_['learning_rate']}, "
              f"leaves={lgbm_rs.best_params_['num_leaves']}, "
              f"CV-F1={lgbm_rs.best_score_:.4f}")
    except Exception as e:
        print(f"  ⚠️ RandomizedSearch failed ({e}), fitting default")
        lgbm_clf = lgb.LGBMClassifier(
            n_estimators=200, max_depth=8, learning_rate=0.1,
            class_weight="balanced", random_state=42, n_jobs=-1, verbose=-1
        )
        lgbm_clf.fit(X_train_tfidf, y_train)
    eval_model("LGBM", lgbm_clf, X_train_tfidf, y_train, X_val_tfidf, y_val, t0)

    # ========================
    # 🔟 Build Stacking Ensemble (Phase 3)
    # ========================
    print("\n🏗️  Building 5-model StackingClassifier...")
    t0 = time.time()
    estimators = [
        ("lr", lr_best),
        ("rf", rf_clf),
        ("sgd", sgd_clf),
        ("svc", svc_clf),
        ("lgbm", lgbm_clf),
    ]

    # StackingClassifier: each base model's predict_proba is fed to a
    # LogisticRegression meta-learner that learns optimal combination weights.
    # cv=3 means base models are re-trained on CV folds to avoid leakage.
    stacking_clf = StackingClassifier(
        estimators=estimators,
        final_estimator=LogisticRegression(max_iter=1000, random_state=42),
        cv=3,
        stack_method="predict_proba",
        n_jobs=-1,
        passthrough=False,
    )
    stacking_clf.fit(X_train_tfidf, y_train)
    n_models = len(estimators)
    print(f"✅ Stacking ensemble created: {n_models} base models + LR meta-learner ({time.time()-t0:.1f}s)")

    # ========================
    # 1️⃣1️⃣ Note on calibration
    # ========================
    # The StackingClassifier's LR meta-learner already produces well-calibrated
    # probabilities (logistic regression is inherently calibrated). Wrapping it
    # in another CalibratedClassifierCV is redundant and expensive.
    # We use the stacking output directly.
    calibrated = stacking_clf
    print("\n✅ Using stacking meta-learner probabilities directly (LR is inherently calibrated)")

    # ========================
    # 1️⃣2️⃣ Find optimal threshold (on clean validation data)
    # ========================
    print("\n🔍 Finding optimal threshold...")
    proba_val = calibrated.predict_proba(X_val_tfidf)[:, 1]
    fpr, tpr, thresholds = roc_curve(y_val, proba_val)
    j_scores = tpr - fpr
    best_thr = float(np.round(thresholds[np.argmax(j_scores)], 3))
    print(f"✅ Optimal threshold: {best_thr}")

    # ========================
    # 1️⃣3️⃣ Evaluate test set
    # ========================
    print("\n📊 Evaluating on test set...")
    proba_test = calibrated.predict_proba(X_test_tfidf)[:, 1]
    y_test_pred = (proba_test >= best_thr).astype(int)

    acc = accuracy_score(y_test, y_test_pred)
    p, r, f1, _ = precision_recall_fscore_support(y_test, y_test_pred, average="binary")
    auc = roc_auc_score(y_test, proba_test)

    print("\n" + "=" * 80)
    print("🏆 TEST SET PERFORMANCE:")
    print("=" * 80)
    print(f"Accuracy:  {acc:.4f}")
    print(f"Precision: {p:.4f}")
    print(f"Recall:    {r:.4f}")
    print(f"F1-Score:  {f1:.4f}")
    print(f"ROC-AUC:   {auc:.4f}")
    print("\nConfusion Matrix:")
    print(confusion_matrix(y_test, y_test_pred))
    print("\nClassification Report:")
    print(classification_report(y_test, y_test_pred, target_names=["FAKE", "REAL"]))
    print("=" * 80)

    total_time = time.time() - t_start
    print(f"\n⏱️  Total training time: {total_time:.0f}s ({total_time/60:.1f} min)")

    # Save plots
    save_plots(y_test, y_test_pred, proba_test)

    # Log experiment
    metrics = {
        "accuracy": acc,
        "precision": p,
        "recall": r,
        "f1": f1,
        "roc_auc": auc,
        "threshold": best_thr
    }
    params = {
        "model": "Stacking (LR+RF+SGD+SVC+LGBM) + Meta + RandSearch",
        "n_samples": len(df),
        "features": int(X_train_tfidf.shape[1]),
        "meta_features": N_META_FEATURES,
        "version": "4.3_phase4"
    }
    log_experiment(metrics, params)

    # ========================
    # 1️⃣4️⃣ Save model (FIXED: proper train/serve alignment)
    # ========================
    print("\n💾 Saving model and config...")

    # For serving, we need to save:
    # 1. tfidf.joblib — fitted TF-IDF vectorizer
    # 2. model.joblib — calibrated ensemble (expects combined TF-IDF + meta input)
    # 3. scaler.joblib — StandardScaler for meta features (Phase 2)
    # 
    # At inference: tfidf.transform(cleaned) → hstack with scaler.transform(meta) → model.predict_proba()

    # Save versioned artifacts
    version_tag = datetime.now().strftime("%Y%m%d_%H%M%S")
    version_dir = MODEL_DIR / f"v_{version_tag}"
    version_dir.mkdir(exist_ok=True)

    config_data = {
        "threshold": best_thr,
        "accuracy": float(acc),
        "precision": float(p),
        "recall": float(r),
        "f1_score": float(f1),
        "roc_auc": float(auc),
        "training_date": str(pd.Timestamp.now()),
        "model_type": "Stacking (LR+RF+SGD+SVC+LGBM) + Meta, Calibrated",
        "n_models": n_models,
        "total_training_samples": len(df),
        "tfidf_features": int(X_train_tfidf_raw.shape[1]),
        "meta_features": N_META_FEATURES,
        "total_features": int(X_train_tfidf.shape[1]),
        "meta_feature_names": FEATURE_NAMES,
        "version": version_tag,
        "datasets_used": list(df["source_dataset"].unique()) if "source_dataset" in df.columns else [],
    }

    # Save to BOTH versioned dir and latest (models/) location
    for target_dir in [version_dir, MODEL_DIR]:
        dump(calibrated, target_dir / "model.joblib")
        dump(tfidf, target_dir / "tfidf.joblib")
        dump(scaler, target_dir / "scaler.joblib")  # Phase 2: meta feature scaler
        with open(target_dir / "config.json", "w") as f:
            json.dump(config_data, f, indent=2)

    print(f"✅ Saved model  → {MODEL_DIR / 'model.joblib'}")
    print(f"✅ Saved tfidf  → {MODEL_DIR / 'tfidf.joblib'}")
    print(f"✅ Saved scaler → {MODEL_DIR / 'scaler.joblib'}")
    print(f"✅ Saved config → {MODEL_DIR / 'config.json'}")
    print(f"✅ Versioned copy → {version_dir}")
    print("\n" + "=" * 80)
    print("🎉 TRAINING COMPLETE - ACCURACY: {:.2f}%".format(acc*100))
    print("=" * 80)

if __name__ == "__main__":
    main()
