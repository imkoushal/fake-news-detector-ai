"""
Hybrid Fake News Detector - Model Training
Features:
- Multiple ensemble classifiers (LR, SVM, RF)
- Advanced TF-IDF feature engineering
- Extensive hyperparameter tuning
- Cross-validation with stratification
- Calibrated probability predictions
- High accuracy optimization
- Experiment logging and visualization
"""

import os
import json
import sys
from pathlib import Path
import warnings
import csv
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns

warnings.filterwarnings("ignore")

# Fix encoding issues on Windows
if sys.platform.startswith('win'):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split, StratifiedKFold, GridSearchCV
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.svm import LinearSVC
from sklearn.ensemble import VotingClassifier, RandomForestClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.base import clone, BaseEstimator, ClassifierMixin
from sklearn.metrics import (
    accuracy_score, precision_recall_fscore_support,
    classification_report, confusion_matrix, roc_auc_score, roc_curve
)
from joblib import dump

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
DATA_DIR = Path("data")
MODEL_DIR = Path("models")
LOGS_DIR = Path("logs")
MODEL_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

FILES = {
    "true": [
        DATA_DIR / "True.csv",
        DATA_DIR / "True_new.csv",
        DATA_DIR / "True_old_backup.csv",
    ],
    "fake": [
        DATA_DIR / "Fake.csv",
        DATA_DIR / "Fake_new.csv",
        DATA_DIR / "Fake_old_backup.csv",
    ]
}

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

def main():
    print("=" * 80)
    print("🚀 HYBRID FAKE NEWS DETECTION - TRAINING PIPELINE")
    print("=" * 80)

    # ========================
    # 1️⃣ Load datasets
    # ========================
    print("\n📂 Loading datasets...")
    dfs = []

    # Load all true news files
    for true_file in FILES["true"]:
        if true_file.exists():
            df_true = pd.read_csv(true_file, encoding="utf-8", on_bad_lines="skip")
            df_true["label"] = 1
            dfs.append(df_true)
            print(f"✅ Loaded {true_file.name} → {len(df_true)} rows")
        else:
            print(f"⚠️  {true_file.name} not found (skipping)")

    # Load all fake news files
    for fake_file in FILES["fake"]:
        if fake_file.exists():
            df_fake = pd.read_csv(fake_file, encoding="utf-8", on_bad_lines="skip")
            df_fake["label"] = 0
            dfs.append(df_fake)
            print(f"✅ Loaded {fake_file.name} → {len(df_fake)} rows")
        else:
            print(f"⚠️  {fake_file.name} not found (skipping)")

    if not dfs:
        print("❌ No dataset files found in 'data/'. Please add CSV files.")
        return

    # ========================
    # 2️⃣ Combine and clean
    # ========================
    print("\n🧹 Combining and cleaning data...")
    df = pd.concat(dfs, ignore_index=True)

    # Identify text column
    text_cols = [col for col in ["title", "text", "content"] if col in df.columns]
    if not text_cols:
        print("❌ No text column found. Expected 'title', 'text', or 'content'")
        return

    primary_col = text_cols[0]
    df[primary_col] = df[primary_col].fillna("").astype(str)
    df["content"] = df[primary_col].str.strip()

    # Handle multiple text columns
    for col in text_cols[1:]:
        if col in df.columns:
            df[col] = df[col].fillna("").astype(str)
            df["content"] = df["content"] + " " + df[col].str.strip()

    df["content"] = df["content"].str.replace(r"\s+", " ", regex=True).str.strip()
    df = df[df["content"].str.len() > 10].drop_duplicates(subset="content").reset_index(drop=True)

    print(f"✅ Combined dataset shape: {df.shape}")
    print(f"📊 Label distribution:\n{df['label'].value_counts()}")

    # ========================
    # 3️⃣ Balance dataset
    # ========================
    print("\n⚖️  Balancing dataset...")
    min_count = df["label"].value_counts().min()
    df = df.groupby("label", group_keys=False).apply(
        lambda x: x.sample(min(min_count, len(x)), random_state=42)
    ).reset_index(drop=True)
    print(f"✅ Balanced: {dict(df['label'].value_counts())}")

    # ========================
    # 4️⃣ Clean text
    # ========================
    print("\n🔤 Cleaning text...")
    # Use a smaller sample for quick testing if needed, or full dataset
    # df = df.sample(min(1000, len(df))) # Uncomment for quick debug
    df["content_clean"] = df["content"].apply(clean_text)
    df = df[df["content_clean"].str.len() > 5].reset_index(drop=True)
    print(f"✅ Dataset after cleaning: {len(df)} rows")

    # ========================
    # 5️⃣ Split data
    # ========================
    print("\n✂️  Splitting data...")
    X = df["content_clean"]
    y = df["label"]

    X_temp, X_test, y_temp, y_test = train_test_split(
        X, y, test_size=0.15, stratify=y, random_state=42
    )
    X_train, X_val, y_train, y_val = train_test_split(
        X_temp, y_temp, test_size=0.1765, stratify=y_temp, random_state=42
    )

    print(f"✅ Train: {len(X_train)}, Val: {len(X_val)}, Test: {len(X_test)}")

    # ========================
    # 6️⃣ Build TF-IDF
    # ========================
    print("\n📝 Building TF-IDF vectorizer...")
    tfidf = TfidfVectorizer(
        ngram_range=(1, 3),
        min_df=2,
        max_df=0.90,
        sublinear_tf=True,
        max_features=5000,
        stop_words="english"
    )

    # ========================
    # 7️⃣ Train LR
    # ========================
    print("\n🎯 Training Logistic Regression...")
    lr_pipe = Pipeline([
        ("tfidf", tfidf),
        ("clf", LogisticRegression(max_iter=1000, class_weight="balanced", random_state=42))
    ])

    lr_params = {"clf__C": [0.5, 1.0, 2.0]}
    
    # Adjust CV splits for small datasets
    n_splits = 5
    if len(X_train) < 50:
        n_splits = 2
        print(f"⚠️ Small dataset detected ({len(X_train)} samples). Reducing CV splits to {n_splits}.")
        
    cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)
    lr_gs = GridSearchCV(lr_pipe, lr_params, scoring="f1", cv=cv, n_jobs=-1, verbose=1)
    
    try:
        lr_gs.fit(X_train, y_train)
        print(f"✅ LR Best params: {lr_gs.best_params_}, F1: {lr_gs.best_score_:.4f}")
        lr_best = lr_gs.best_estimator_
    except Exception as e:
        print(f"❌ Error training LR: {e}")
        # Fallback to simple fit
        lr_pipe.fit(X_train, y_train)
        lr_best = lr_pipe

    # ========================
    # 8️⃣ Train Random Forest
    # ========================
    print("\n🎯 Training Random Forest...")
    rf_pipe = Pipeline([
        ("tfidf", clone(tfidf)),
        ("clf", RandomForestClassifier(n_estimators=150, max_depth=15, class_weight="balanced", random_state=42, n_jobs=-1))
    ])

    # No hyperparameter tuning needed for RF as it's computationally expensive
    rf_best = rf_pipe
    rf_best.fit(X_train, y_train)
    
    try:
        rf_f1 = roc_auc_score(y_val, rf_best.predict_proba(X_val)[:, 1])
        print(f"✅ Random Forest ROC-AUC: {rf_f1:.4f}")
    except Exception as e:
        print(f"⚠️ Could not calculate RF AUC: {e}")

    # ========================
    # 9️⃣ Create Ensemble
    # ========================
    print("\n🎯 Creating ensemble model...")
    estimators = [("lr", lr_best), ("rf", rf_best)]

    voting_clf = VotingClassifier(estimators=estimators, voting="soft", n_jobs=-1)
    voting_clf.fit(X_train, y_train)
    print(f"✅ Ensemble created with {len(estimators)} models")

    # ========================
    # 🔟 Calibrate
    # ========================
    print("\n⚖️  Calibrating predictions...")
    # Adjust CV for calibration too
    cal_cv = 3
    if len(X_train) < 50:
        cal_cv = "prefit" # Use prefit if too small, or just 2
        # Actually prefit requires the model to be already fitted, which it is.
        # But CalibratedClassifierCV with cv='prefit' expects the base estimator to be fitted.
        # voting_clf IS fitted.
        
    if cal_cv == "prefit":
         calibrated = CalibratedClassifierCV(voting_clf, method="sigmoid", cv="prefit")
         calibrated.fit(X_val, y_val) # Fit on validation set if prefit? No, prefit means it's already fitted.
         # Wait, if cv='prefit', X and y in fit() are used for calibration.
         # So we should pass X_val, y_val.
    else:
        calibrated = CalibratedClassifierCV(voting_clf, method="sigmoid", cv=cal_cv)
        X_trval = pd.concat([X_train, X_val])
        y_trval = pd.concat([y_train, y_val])
        calibrated.fit(X_trval, y_trval)

    # ========================
    # 1️⃣1️⃣ Find optimal threshold
    # ========================
    print("\n🔍 Finding optimal threshold...")
    proba_val = calibrated.predict_proba(X_val)[:, 1]
    fpr, tpr, thresholds = roc_curve(y_val, proba_val)
    j_scores = tpr - fpr
    best_thr = float(np.round(thresholds[np.argmax(j_scores)], 3))
    print(f"✅ Optimal threshold: {best_thr}")

    # ========================
    # 1️⃣2️⃣ Evaluate test set
    # ========================
    print("\n📊 Evaluating on test set...")
    proba_test = calibrated.predict_proba(X_test)[:, 1]
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
        "model": "Ensemble (LR+RF)",
        "n_samples": len(df),
        "features": 5000
    }
    log_experiment(metrics, params)

    # ========================
    # 1️⃣3️⃣ Save model
    # ========================
    print("\n💾 Saving model and config...")

    class FinalModel(BaseEstimator, ClassifierMixin):
        def __init__(self, model):
            self.model = model
        def fit(self, X, y):
            return self
        def predict(self, X):
            return self.model.predict(X)
        def predict_proba(self, X):
            return self.model.predict_proba(X)

    final_model = FinalModel(calibrated)
    PIPE_PATH = MODEL_DIR / "pipeline.joblib"
    CFG_PATH = MODEL_DIR / "config.json"

    dump(final_model, PIPE_PATH)

    config_data = {
        "threshold": best_thr,
        "accuracy": float(acc),
        "precision": float(p),
        "recall": float(r),
        "f1_score": float(f1),
        "roc_auc": float(auc),
        "training_date": str(pd.Timestamp.now()),
        "model_type": "ensemble",
        "n_models": len(estimators)
    }

    with open(CFG_PATH, "w") as f:
        json.dump(config_data, f, indent=2)

    print(f"✅ Saved → {PIPE_PATH}")
    print(f"✅ Saved → {CFG_PATH}")
    print("\n" + "=" * 80)
    print("🎉 TRAINING COMPLETE - ACCURACY: {:.2f}%".format(acc*100))
    print("=" * 80)

if __name__ == "__main__":
    main()
