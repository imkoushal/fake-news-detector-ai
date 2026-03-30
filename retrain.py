"""
Fake News Detection — Improved Retrain Script
- Less aggressive preprocessing (keeps more signal for real news)
- Higher TF-IDF features (8000)
- Support for custom real news samples
- Uncertainty threshold in evaluation
"""

import sys
import os
import warnings

warnings.filterwarnings("ignore")

if sys.platform.startswith("win"):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

import re
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import LinearSVC
from sklearn.calibration import CalibratedClassifierCV
from sklearn.pipeline import Pipeline
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
)
from joblib import dump


# =============================================================================
# CONFIG
# =============================================================================
MODEL_DIR = Path("models")
MODEL_DIR.mkdir(exist_ok=True)
OUTPUT_PATH = MODEL_DIR / "pipeline_svm.joblib"
CUSTOM_REAL_PATH = Path("data") / "custom_real.csv"
CUSTOM_FAKE_PATH = Path("data") / "custom_fake.csv"
UNCERTAINTY_THRESHOLD = 0.1  # if |p_real - p_fake| < this → UNCERTAIN


# =============================================================================
# 1. GENTLE CLEAN_TEXT — keeps more natural language signal
# =============================================================================
def clean_text(text: str) -> str:
    """
    Light preprocessing — avoids stripping too much context.
    Keeps punctuation/numbers out but preserves natural word flow.
    """
    text = str(text).lower()
    text = re.sub(r"http\S+|www\.\S+", " ", text)            # URLs
    text = re.sub(r"<[^>]+>", " ", text)                      # HTML tags
    text = re.sub(r"@\w+", " ", text)                         # mentions
    text = re.sub(r"[^a-z\s']", " ", text)                    # keep apostrophes
    text = re.sub(r"\s+", " ", text).strip()
    return text


# =============================================================================
# 2. LOAD DATASETS
# =============================================================================
def load_data() -> pd.DataFrame:
    """Load True.csv + Fake.csv from data_new/, plus any custom samples."""
    data_dir = Path("data_new")

    true_path = data_dir / "True.csv"
    fake_path = data_dir / "Fake.csv"

    if not true_path.exists() or not fake_path.exists():
        print("❌ data_new/True.csv or data_new/Fake.csv not found!")
        sys.exit(1)

    print("📂 Loading datasets from data_new/ ...")
    df_true = pd.read_csv(true_path, encoding="utf-8", on_bad_lines="skip")
    df_fake = pd.read_csv(fake_path, encoding="utf-8", on_bad_lines="skip")

    # Label: 0 = FAKE, 1 = REAL
    df_true["label"] = 1
    df_fake["label"] = 0

    print(f"  ✅ True news rows : {len(df_true)}")
    print(f"  ✅ Fake news rows : {len(df_fake)}")

    frames = [df_true, df_fake]

    # --- Load custom samples if they exist ---
    if CUSTOM_REAL_PATH.exists():
        df_custom_real = pd.read_csv(CUSTOM_REAL_PATH, encoding="utf-8", on_bad_lines="skip")
        df_custom_real["label"] = 1
        frames.append(df_custom_real)
        print(f"  ✅ Custom REAL samples: {len(df_custom_real)}")

    if CUSTOM_FAKE_PATH.exists():
        df_custom_fake = pd.read_csv(CUSTOM_FAKE_PATH, encoding="utf-8", on_bad_lines="skip")
        df_custom_fake["label"] = 0
        frames.append(df_custom_fake)
        print(f"  ✅ Custom FAKE samples: {len(df_custom_fake)}")

    df = pd.concat(frames, ignore_index=True)
    return df


# =============================================================================
# 3. MAIN TRAINING PIPELINE
# =============================================================================
def main():
    print("=" * 70)
    print("🚀  FAKE NEWS DETECTION — IMPROVED RETRAIN")
    print("=" * 70)

    # --- Load ---
    df = load_data()

    # Identify text column
    text_col = None
    for col in ["text", "title", "content"]:
        if col in df.columns:
            text_col = col
            break
    if text_col is None:
        print("❌ No text column found"); sys.exit(1)

    df["content"] = df[text_col].fillna("").astype(str)

    # Merge title + text for richer signal
    if "title" in df.columns and text_col != "title":
        df["content"] = df["title"].fillna("") + " " + df["content"]

    df = df[df["content"].str.len() > 20].drop_duplicates(subset="content").reset_index(drop=True)
    print(f"\n📊 Total rows after dedup: {len(df)}")

    # --- Balance ---
    print("\n⚖️  Balancing classes ...")
    counts = df["label"].value_counts()
    print(f"   Before: {dict(counts)}")
    min_count = counts.min()
    df = (
        df.groupby("label", group_keys=False)
        .apply(lambda x: x.sample(min_count, random_state=42))
        .reset_index(drop=True)
    )
    print(f"   After:  {dict(df['label'].value_counts())}")

    # --- Clean text (gentle) ---
    print("\n🔤 Cleaning text (gentle mode) ...")
    df["clean"] = df["content"].apply(clean_text)
    df = df[df["clean"].str.len() > 10].reset_index(drop=True)
    print(f"   Rows after cleaning: {len(df)}")

    # --- Split ---
    X = df["clean"]
    y = df["label"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42
    )
    print(f"\n✂️  Train: {len(X_train)}  |  Test: {len(X_test)}")

    # --- Build Pipeline (improved TF-IDF) ---
    print("\n🏗️  Building improved SVM pipeline ...")
    pipeline = Pipeline([
        ("tfidf", TfidfVectorizer(
            max_features=8000,
            ngram_range=(1, 2),
            sublinear_tf=True,
            min_df=2,
            max_df=0.9,
            stop_words="english",
        )),
        ("svm", CalibratedClassifierCV(
            LinearSVC(
                class_weight="balanced",
                max_iter=3000,
                C=1.0,
                random_state=42,
            ),
            cv=5,
            method="sigmoid",
        )),
    ])

    pipeline.fit(X_train, y_train)
    print("   ✅ Pipeline fitted")

    # --- Evaluate ---
    y_pred = pipeline.predict(X_test)
    acc = accuracy_score(y_test, y_pred)

    print("\n" + "=" * 70)
    print(f"🏆  TEST ACCURACY: {acc*100:.2f}%")
    print("=" * 70)
    print("\nConfusion Matrix:")
    print(confusion_matrix(y_test, y_pred))
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred, target_names=["FAKE", "REAL"]))

    # --- Evaluate with uncertainty threshold ---
    print(f"\n🔍 Uncertainty analysis (threshold={UNCERTAINTY_THRESHOLD}):")
    y_proba = pipeline.predict_proba(X_test)
    uncertain_count = 0
    correct_certain = 0
    total_certain = 0

    for i in range(len(y_proba)):
        p_fake, p_real = y_proba[i]
        diff = abs(p_real - p_fake)

        if diff < UNCERTAINTY_THRESHOLD:
            uncertain_count += 1
        else:
            total_certain += 1
            pred = 1 if p_real > p_fake else 0
            if pred == y_test.iloc[i]:
                correct_certain += 1

    certain_acc = correct_certain / total_certain if total_certain > 0 else 0
    print(f"   Total test samples : {len(y_test)}")
    print(f"   Uncertain (skipped): {uncertain_count} ({uncertain_count/len(y_test)*100:.1f}%)")
    print(f"   Certain predictions : {total_certain}")
    print(f"   Accuracy (certain) : {certain_acc*100:.2f}%")

    # --- Debug predictions ---
    print("\n🔍 Debug — Sample predictions:")
    samples = [
        ("BREAKING: Scientists confirm the earth is flat and NASA has been lying for decades!", "FAKE"),
        ("The stock market saw a 2% increase today following the Federal Reserve's announcement on interest rates.", "REAL"),
        ("You won't BELIEVE what this celebrity did! Doctors HATE this trick!", "FAKE"),
        ("The United Nations held a summit on climate change, with representatives from 190 countries attending.", "REAL"),
        ("Secret underground alien base discovered under the White House!", "FAKE"),
        ("President signs bipartisan infrastructure bill into law after months of negotiations.", "REAL"),
        ("India's GDP grew 7.8% in Q3, led by manufacturing and services sector expansion.", "REAL"),
        ("EXPOSED: Government secretly replacing water with mind-control chemicals!", "FAKE"),
        ("The Federal Reserve held interest rates steady at its latest policy meeting.", "REAL"),
        ("hi", "SHORT"),
    ]

    for text, expected in samples:
        cleaned = clean_text(text)

        # Short text check
        if len(cleaned.split()) < 5:
            print(f"  [UNCERTAIN] (too short)  expected={expected}  → \"{text[:60]}\"")
            continue

        proba = pipeline.predict_proba([cleaned])[0]
        p_fake, p_real = proba
        diff = abs(p_real - p_fake)

        if diff < UNCERTAINTY_THRESHOLD:
            label = "UNCERTAIN"
            confidence = max(p_fake, p_real)
        else:
            pred = 1 if p_real > p_fake else 0
            label = "REAL" if pred == 1 else "FAKE"
            confidence = proba[pred]

        status = "✅" if label == expected else "❌"
        print(f"  {status} [{label}] conf={confidence:.3f}  expected={expected}  → \"{text[:60]}\"")

    # --- Save ---
    dump(pipeline, OUTPUT_PATH)
    print(f"\n💾 Model saved → {OUTPUT_PATH}")
    print(f"   File size: {OUTPUT_PATH.stat().st_size / 1024 / 1024:.1f} MB")
    print("\n✅ Done! Restart the backend to use the new model.")


if __name__ == "__main__":
    main()
