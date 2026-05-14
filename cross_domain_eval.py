"""
Cross-Domain Validation — Phase 4.3

Evaluates model generalization by training on each dataset source and testing
on all others. This reveals whether the model learns true fake-news signals
or just memorizes dataset-specific artifacts (writing style, topic distribution).

Produces a generalization matrix:
  Train\Test    | Fake/True  | WELFake   | LIAR
  Fake/True     |    —       | 0.82      | 0.65
  WELFake       |   0.79     |    —      | 0.62
  LIAR          |   0.58     |  0.60     |   —

Also trains a "combined" model on all datasets for comparison.

Usage:
    py cross_domain_eval.py
"""

import os
import sys
import json
import time
from pathlib import Path
import warnings

warnings.filterwarnings("ignore")

# Fix encoding issues on Windows
if sys.platform.startswith('win'):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', line_buffering=True)

import numpy as np
import pandas as pd
import scipy.sparse as sp
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score, precision_recall_fscore_support, roc_auc_score,
    f1_score
)

from utils import clean_text
from meta_features import extract_batch, N_META_FEATURES, FEATURE_NAMES

# Paths
DATA_DIR = Path("data_new")
LIAR_DIR = DATA_DIR / "liar"
LOGS_DIR = Path("logs")
LOGS_DIR.mkdir(exist_ok=True)


# ========================
# Dataset Loaders (reused from train.py)
# ========================

def load_faketrue(data_dir: Path) -> pd.DataFrame:
    """Load True.csv + Fake.csv as a single labeled dataset."""
    dfs = []
    for csv_file in sorted(data_dir.glob("True*.csv")):
        try:
            df = pd.read_csv(csv_file, encoding="utf-8", on_bad_lines="skip")
            df["label"] = 1
            dfs.append(df)
        except Exception:
            pass
    for csv_file in sorted(data_dir.glob("Fake*.csv")):
        try:
            df = pd.read_csv(csv_file, encoding="utf-8", on_bad_lines="skip")
            df["label"] = 0
            dfs.append(df)
        except Exception:
            pass
    if not dfs:
        return pd.DataFrame()
    combined = pd.concat(dfs, ignore_index=True)
    # Resolve text column
    text_cols = [c for c in ["title", "text", "content"] if c in combined.columns]
    if not text_cols:
        return pd.DataFrame()
    combined["content"] = combined[text_cols[0]].fillna("").astype(str)
    for c in text_cols[1:]:
        combined["content"] = combined["content"] + " " + combined[c].fillna("").astype(str)
    combined["content"] = combined["content"].str.replace(r"\s+", " ", regex=True).str.strip()
    combined = combined[combined["content"].str.len() > 10].reset_index(drop=True)
    return combined[["content", "label"]]


def load_welfake(data_dir: Path) -> pd.DataFrame:
    """Load WELFake dataset."""
    path = data_dir / "WELFake_Dataset.csv"
    if not path.exists():
        return pd.DataFrame()
    try:
        df = pd.read_csv(path, encoding="utf-8", on_bad_lines="skip")
        if "label" in df.columns and "text" in df.columns:
            df["label"] = df["label"].map({0: 1, 1: 0})
            df = df.dropna(subset=["label"])
            df["label"] = df["label"].astype(int)
            df["content"] = df["text"].fillna("").astype(str).str.strip()
            df = df[df["content"].str.len() > 10].reset_index(drop=True)
            return df[["content", "label"]]
    except Exception:
        pass
    return pd.DataFrame()


def load_liar(liar_dir: Path) -> pd.DataFrame:
    """Load and binarize the LIAR dataset."""
    if not liar_dir.exists():
        return pd.DataFrame()
    FAKE_LABELS = {"pants-fire", "false", "barely-true"}
    REAL_LABELS = {"true", "mostly-true"}
    dfs = []
    for tsv in ["train.tsv", "valid.tsv", "test.tsv"]:
        path = liar_dir / tsv
        if not path.exists():
            continue
        try:
            df = pd.read_csv(path, sep="\t", header=None, usecols=[1, 2],
                             names=["raw_label", "text"], on_bad_lines="skip")
            df = df[df["raw_label"].isin(FAKE_LABELS | REAL_LABELS)].copy()
            df["label"] = df["raw_label"].apply(lambda x: 0 if x in FAKE_LABELS else 1)
            df["content"] = df["text"].fillna("").astype(str).str.strip()
            dfs.append(df[["content", "label"]])
        except Exception:
            pass
    if not dfs:
        return pd.DataFrame()
    combined = pd.concat(dfs, ignore_index=True)
    combined = combined[combined["content"].str.len() > 10].reset_index(drop=True)
    return combined


def load_generic(data_dir: Path) -> pd.DataFrame:
    """Load data.csv."""
    path = data_dir / "data.csv"
    if not path.exists():
        return pd.DataFrame()
    try:
        df = pd.read_csv(path, encoding="utf-8", on_bad_lines="skip")
        if "Label" in df.columns:
            text_col = "Body" if "Body" in df.columns else "Headline" if "Headline" in df.columns else None
            if text_col:
                df = df[[text_col, "Label"]].copy()
                df.columns = ["content", "label"]
                if df["label"].dtype == object:
                    label_map = {"fake": 0, "false": 0, "real": 1, "true": 1, "1": 1, "0": 0}
                    df["label"] = df["label"].str.lower().str.strip().map(label_map)
                    df = df.dropna(subset=["label"])
                    df["label"] = df["label"].astype(int)
                df["content"] = df["content"].fillna("").astype(str).str.strip()
                df = df[df["content"].str.len() > 10].reset_index(drop=True)
                return df[["content", "label"]]
    except Exception:
        pass
    return pd.DataFrame()


# ========================
# Feature Pipeline
# ========================

def build_features(texts_clean, texts_raw, tfidf=None, scaler=None, fit=False):
    """
    Build combined TF-IDF + meta feature matrix.
    If fit=True, fits tfidf and scaler on the data and returns them.
    """
    if fit:
        tfidf = TfidfVectorizer(
            ngram_range=(1, 3), min_df=2, max_df=0.85,
            sublinear_tf=True, max_features=15000, stop_words="english"
        )
        X_tfidf = tfidf.fit_transform(texts_clean)
        meta = extract_batch(texts_raw)
        scaler = StandardScaler()
        meta_scaled = scaler.fit_transform(meta)
    else:
        X_tfidf = tfidf.transform(texts_clean)
        meta = extract_batch(texts_raw)
        meta_scaled = scaler.transform(meta)

    X_combined = sp.hstack([X_tfidf, sp.csr_matrix(meta_scaled)], format="csr")
    return X_combined, tfidf, scaler


def clean_batch(texts, batch_name=""):
    """Clean a batch of texts with progress."""
    total = len(texts)
    batch_size = max(1, total // 10)
    cleaned = []
    for i, text in enumerate(texts):
        cleaned.append(clean_text(str(text)))
        if (i + 1) % batch_size == 0 or (i + 1) == total:
            pct = (i + 1) / total * 100
            if batch_name:
                print(f"    Cleaning {batch_name}: {i+1:,}/{total:,} ({pct:.0f}%)", flush=True)
    return cleaned


# ========================
# Cross-Domain Evaluation
# ========================

def cross_domain_eval():
    """Train on each dataset, test on all others."""
    print("=" * 80)
    print("🌐 CROSS-DOMAIN VALIDATION — Phase 4.3")
    print("   Train on each dataset, evaluate on all others")
    print("=" * 80)

    # Load all datasets
    print("\n📂 Loading datasets...")
    datasets = {}

    df_ft = load_faketrue(DATA_DIR)
    if len(df_ft) > 0:
        datasets["FakeTrue"] = df_ft
        print(f"  ✅ FakeTrue: {len(df_ft):,} rows (Fake: {(df_ft['label']==0).sum():,}, Real: {(df_ft['label']==1).sum():,})")

    df_wel = load_welfake(DATA_DIR)
    if len(df_wel) > 0:
        datasets["WELFake"] = df_wel
        print(f"  ✅ WELFake: {len(df_wel):,} rows (Fake: {(df_wel['label']==0).sum():,}, Real: {(df_wel['label']==1).sum():,})")

    df_liar = load_liar(LIAR_DIR)
    if len(df_liar) > 0:
        datasets["LIAR"] = df_liar
        print(f"  ✅ LIAR: {len(df_liar):,} rows (Fake: {(df_liar['label']==0).sum():,}, Real: {(df_liar['label']==1).sum():,})")

    df_gen = load_generic(DATA_DIR)
    if len(df_gen) > 0:
        datasets["DataCSV"] = df_gen
        print(f"  ✅ DataCSV: {len(df_gen):,} rows (Fake: {(df_gen['label']==0).sum():,}, Real: {(df_gen['label']==1).sum():,})")

    if len(datasets) < 2:
        print("❌ Need at least 2 datasets for cross-domain validation.")
        return

    # Balance each dataset (cap at 10K per class for speed)
    MAX_PER_CLASS = 10000
    for name, df in datasets.items():
        min_count = min(df["label"].value_counts().min(), MAX_PER_CLASS)
        parts = []
        for label_val in [0, 1]:
            subset = df[df["label"] == label_val]
            parts.append(subset.sample(min(min_count, len(subset)), random_state=42))
        datasets[name] = pd.concat(parts, ignore_index=True)
        print(f"  ⚖️  {name} balanced: {len(datasets[name]):,} rows")

    # Pre-clean and extract meta features for all datasets
    print("\n🔤 Cleaning text for all datasets...")
    cleaned_datasets = {}
    for name, df in datasets.items():
        t0 = time.time()
        df_copy = df.copy()
        df_copy["content_clean"] = clean_batch(df_copy["content"].values, name)
        df_copy = df_copy[df_copy["content_clean"].str.len() > 5].reset_index(drop=True)
        cleaned_datasets[name] = df_copy
        print(f"  ✅ {name}: {len(df_copy):,} rows cleaned ({time.time()-t0:.1f}s)")

    # Cross-domain evaluation matrix
    print("\n" + "=" * 80)
    print("🏗️  Running cross-domain evaluation...")
    print("=" * 80)

    ds_names = list(cleaned_datasets.keys())
    results_matrix = {}

    for train_name in ds_names:
        train_df = cleaned_datasets[train_name]
        print(f"\n🎯 Training on: {train_name} ({len(train_df):,} rows)...")

        t0 = time.time()

        # Build features (fit on training dataset)
        X_train, tfidf, scaler = build_features(
            train_df["content_clean"].values,
            train_df["content"].values,
            fit=True
        )
        y_train = train_df["label"].values

        # Train a fast LR model
        clf = LogisticRegression(
            max_iter=1000, C=2.0, class_weight="balanced", random_state=42
        )
        clf.fit(X_train, y_train)

        train_time = time.time() - t0
        print(f"  Trained in {train_time:.1f}s")

        # Evaluate on all datasets (including self for in-domain baseline)
        for test_name in ds_names:
            test_df = cleaned_datasets[test_name]

            try:
                X_test, _, _ = build_features(
                    test_df["content_clean"].values,
                    test_df["content"].values,
                    tfidf=tfidf, scaler=scaler, fit=False
                )
                y_test = test_df["label"].values

                y_pred = clf.predict(X_test)
                y_proba = clf.predict_proba(X_test)[:, 1]

                acc = accuracy_score(y_test, y_pred)
                f1 = f1_score(y_test, y_pred, average="binary")
                try:
                    auc = roc_auc_score(y_test, y_proba)
                except ValueError:
                    auc = 0.0

                marker = "📍" if train_name == test_name else "🔄"
                label = "(in-domain)" if train_name == test_name else "(cross-domain)"
                print(f"  {marker} {train_name} → {test_name}: "
                      f"Acc={acc:.4f}, F1={f1:.4f}, AUC={auc:.4f} {label}")

                results_matrix[f"{train_name}→{test_name}"] = {
                    "accuracy": round(acc, 4),
                    "f1": round(f1, 4),
                    "auc": round(auc, 4),
                    "type": "in-domain" if train_name == test_name else "cross-domain"
                }
            except Exception as e:
                print(f"  ⚠️  {train_name} → {test_name}: Error — {e}")
                results_matrix[f"{train_name}→{test_name}"] = {
                    "accuracy": 0.0, "f1": 0.0, "auc": 0.0, "type": "error"
                }

    # Evaluate "Combined" model
    print(f"\n🎯 Training on: ALL COMBINED ({sum(len(d) for d in cleaned_datasets.values()):,} rows)...")
    combined_df = pd.concat(list(cleaned_datasets.values()), ignore_index=True)
    # Balance combined
    min_c = combined_df["label"].value_counts().min()
    parts = []
    for lv in [0, 1]:
        parts.append(combined_df[combined_df["label"] == lv].sample(min_c, random_state=42))
    combined_df = pd.concat(parts, ignore_index=True)

    t0 = time.time()
    X_combined, tfidf_comb, scaler_comb = build_features(
        combined_df["content_clean"].values,
        combined_df["content"].values,
        fit=True
    )
    y_combined = combined_df["label"].values

    # Use a held-out split for evaluation
    from sklearn.model_selection import train_test_split
    X_comb_train, X_comb_test, y_comb_train, y_comb_test = train_test_split(
        X_combined, y_combined, test_size=0.2, stratify=y_combined, random_state=42
    )
    clf_combined = LogisticRegression(
        max_iter=1000, C=2.0, class_weight="balanced", random_state=42
    )
    clf_combined.fit(X_comb_train, y_comb_train)

    for test_name in ds_names:
        test_df = cleaned_datasets[test_name]
        try:
            X_test, _, _ = build_features(
                test_df["content_clean"].values,
                test_df["content"].values,
                tfidf=tfidf_comb, scaler=scaler_comb, fit=False
            )
            y_test = test_df["label"].values
            y_pred = clf_combined.predict(X_test)
            y_proba = clf_combined.predict_proba(X_test)[:, 1]
            acc = accuracy_score(y_test, y_pred)
            f1 = f1_score(y_test, y_pred, average="binary")
            try:
                auc = roc_auc_score(y_test, y_proba)
            except ValueError:
                auc = 0.0
            print(f"  🌐 Combined → {test_name}: "
                  f"Acc={acc:.4f}, F1={f1:.4f}, AUC={auc:.4f}")
            results_matrix[f"Combined→{test_name}"] = {
                "accuracy": round(acc, 4), "f1": round(f1, 4),
                "auc": round(auc, 4), "type": "combined"
            }
        except Exception as e:
            print(f"  ⚠️  Combined → {test_name}: Error — {e}")

    # Also evaluate combined on its own test split
    y_pred_comb = clf_combined.predict(X_comb_test)
    y_proba_comb = clf_combined.predict_proba(X_comb_test)[:, 1]
    acc_comb = accuracy_score(y_comb_test, y_pred_comb)
    f1_comb = f1_score(y_comb_test, y_pred_comb, average="binary")
    auc_comb = roc_auc_score(y_comb_test, y_proba_comb)
    print(f"  🌐 Combined → Combined (holdout): "
          f"Acc={acc_comb:.4f}, F1={f1_comb:.4f}, AUC={auc_comb:.4f}")

    # Print summary matrix
    print("\n" + "=" * 80)
    print("📊 CROSS-DOMAIN GENERALIZATION MATRIX (Accuracy)")
    print("=" * 80)

    # Header
    header = f"{'Train \\ Test':<15}"
    for name in ds_names:
        header += f"  {name:<12}"
    print(header)
    print("-" * len(header))

    # Rows
    all_cross_domain = []
    for train_name in ds_names + ["Combined"]:
        row = f"{train_name:<15}"
        for test_name in ds_names:
            key = f"{train_name}→{test_name}"
            if key in results_matrix:
                val = results_matrix[key]["accuracy"]
                if train_name == test_name:
                    row += f"  {'['+f'{val:.2f}'+']':>12}"  # In-domain
                else:
                    row += f"  {val:>12.4f}"
                    all_cross_domain.append(val)
            else:
                row += f"  {'—':>12}"
        print(row)

    if all_cross_domain:
        avg_cross = np.mean(all_cross_domain)
        print(f"\n📈 Average cross-domain accuracy: {avg_cross:.4f}")
        print(f"   (excludes in-domain and combined results)")

    # Save results
    results_file = LOGS_DIR / "cross_domain_results.json"
    with open(results_file, "w") as f:
        json.dump({
            "timestamp": str(pd.Timestamp.now()),
            "matrix": results_matrix,
            "avg_cross_domain_accuracy": round(float(avg_cross), 4) if all_cross_domain else None,
            "combined_holdout": {
                "accuracy": round(acc_comb, 4),
                "f1": round(f1_comb, 4),
                "auc": round(auc_comb, 4),
            },
            "dataset_sizes": {name: len(df) for name, df in cleaned_datasets.items()},
        }, f, indent=2)
    print(f"\n💾 Results saved to {results_file}")

    print("\n" + "=" * 80)
    print("✅ CROSS-DOMAIN VALIDATION COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    cross_domain_eval()
