"""
Evaluation Report Generator — Phase 6.2

Generates comprehensive model performance reports from:
  - Training logs (logs/experiments.csv)
  - Cross-domain results (logs/cross_domain_results.json)
  - Model config (models/config.json)
  - Production monitor data (analysis_history.db)

Usage:
    python eval_report.py                    # Print report to console
    python eval_report.py --json             # Output JSON
    python eval_report.py --save             # Save to logs/eval_report.json
"""

import json
import csv
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional

PROJECT_ROOT = Path(__file__).resolve().parent
LOGS_DIR = PROJECT_ROOT / "logs"
MODELS_DIR = PROJECT_ROOT / "models"


def load_experiments() -> list:
    """Load experiment history from CSV."""
    csv_path = LOGS_DIR / "experiments.csv"
    if not csv_path.exists():
        return []
    
    experiments = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            experiments.append(row)
    return experiments


def load_config() -> Dict:
    """Load current model config."""
    config_path = MODELS_DIR / "config.json"
    if not config_path.exists():
        return {}
    with open(config_path, "r") as f:
        return json.load(f)


def load_cross_domain() -> Optional[Dict]:
    """Load cross-domain evaluation results."""
    cd_path = LOGS_DIR / "cross_domain_results.json"
    if not cd_path.exists():
        return None
    with open(cd_path, "r") as f:
        return json.load(f)


def load_monitor_stats() -> Optional[Dict]:
    """Load production monitor statistics."""
    try:
        from model_monitor import ModelMonitor
        monitor = ModelMonitor()
        return monitor.get_health_report(days=30)
    except Exception:
        return None


def compute_improvement_trajectory(experiments: list) -> list:
    """Compute phase-over-phase improvements."""
    trajectory = []
    prev = None
    for exp in experiments:
        acc = float(exp.get("accuracy", 0))
        f1 = float(exp.get("f1", 0))
        auc = float(exp.get("roc_auc", 0))

        entry = {
            "timestamp": exp.get("timestamp", ""),
            "model": exp.get("model", ""),
            "version": exp.get("version", exp.get("", "")),
            "accuracy": round(acc, 4),
            "f1": round(f1, 4),
            "roc_auc": round(auc, 4),
            "n_samples": exp.get("n_samples", ""),
            "features": exp.get("features", ""),
        }

        if prev:
            entry["delta_accuracy"] = round(acc - prev["accuracy"], 4)
            entry["delta_f1"] = round(f1 - prev["f1"], 4)
            entry["delta_auc"] = round(auc - prev["roc_auc"], 4)
        else:
            entry["delta_accuracy"] = 0
            entry["delta_f1"] = 0
            entry["delta_auc"] = 0

        trajectory.append(entry)
        prev = entry

    return trajectory


def compute_cross_domain_summary(cd_data: Dict) -> Dict:
    """Summarize cross-domain performance."""
    if not cd_data or "matrix" not in cd_data:
        return {}

    matrix = cd_data["matrix"]

    in_domain = []
    cross_domain = []
    combined = []

    for key, val in matrix.items():
        entry = {"pair": key, **val}
        if val.get("type") == "in-domain":
            in_domain.append(entry)
        elif val.get("type") == "cross-domain":
            cross_domain.append(entry)
        elif val.get("type") == "combined":
            combined.append(entry)

    # Best and worst cross-domain pairs
    if cross_domain:
        best_cd = max(cross_domain, key=lambda x: x.get("accuracy", 0))
        worst_cd = min(cross_domain, key=lambda x: x.get("accuracy", 0))
    else:
        best_cd = worst_cd = None

    return {
        "in_domain_avg_accuracy": round(
            sum(e["accuracy"] for e in in_domain) / len(in_domain), 4
        ) if in_domain else 0,
        "cross_domain_avg_accuracy": cd_data.get("avg_cross_domain_accuracy", 0),
        "combined_holdout": cd_data.get("combined_holdout", {}),
        "best_cross_domain": best_cd,
        "worst_cross_domain": worst_cd,
        "n_in_domain": len(in_domain),
        "n_cross_domain": len(cross_domain),
        "dataset_sizes": cd_data.get("dataset_sizes", {}),
    }


def generate_report() -> Dict:
    """Generate full evaluation report."""
    config = load_config()
    experiments = load_experiments()
    cd_data = load_cross_domain()
    monitor_stats = load_monitor_stats()

    trajectory = compute_improvement_trajectory(experiments)
    cd_summary = compute_cross_domain_summary(cd_data) if cd_data else {}

    # Current model summary
    current = trajectory[-1] if trajectory else {}

    # Compute total improvement from first honest baseline
    first_honest = None
    for t in trajectory:
        if t["accuracy"] < 1.0:  # Skip the overfit baseline
            first_honest = t
            break

    total_improvement = {}
    if first_honest and current:
        total_improvement = {
            "accuracy": round(current["accuracy"] - first_honest["accuracy"], 4),
            "f1": round(current["f1"] - first_honest["f1"], 4),
            "roc_auc": round(current["roc_auc"] - first_honest["roc_auc"], 4),
            "baseline_accuracy": first_honest["accuracy"],
            "current_accuracy": current["accuracy"],
        }

    report = {
        "report_type": "Model Evaluation Report",
        "generated_at": datetime.now().isoformat(),
        "model": {
            "type": config.get("model_type", "Unknown"),
            "version": config.get("version", "Unknown"),
            "training_date": config.get("training_date", "Unknown"),
            "training_samples": config.get("total_training_samples", 0),
            "tfidf_features": config.get("tfidf_features", 0),
            "meta_features": config.get("meta_features", 0),
            "total_features": config.get("total_features", 0),
            "threshold": config.get("threshold", 0.5),
            "datasets_used": config.get("datasets_used", []),
        },
        "performance": {
            "accuracy": config.get("accuracy", 0),
            "precision": config.get("precision", 0),
            "recall": config.get("recall", 0),
            "f1_score": config.get("f1_score", 0),
            "roc_auc": config.get("roc_auc", 0),
        },
        "improvement_trajectory": trajectory,
        "total_improvement": total_improvement,
        "cross_domain": cd_summary,
        "production_health": monitor_stats if monitor_stats else {"status": "NO_DATA"},
        "meta_feature_names": config.get("meta_feature_names", []),
    }

    return report


def print_report(report: Dict):
    """Pretty-print the evaluation report."""
    # Ensure UTF-8 output on Windows
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')
    
    print("=" * 80)
    print("[REPORT] MODEL EVALUATION REPORT")
    print(f"   Generated: {report['generated_at']}")
    print("=" * 80)

    # Model info
    m = report["model"]
    print(f"\n🏗️  Model: {m['type']}")
    print(f"   Version: {m['version']}")
    print(f"   Training Date: {m['training_date']}")
    print(f"   Training Samples: {m['training_samples']:,}")
    print(f"   Features: {m['total_features']} (TF-IDF: {m['tfidf_features']}, Meta: {m['meta_features']})")
    print(f"   Threshold: {m['threshold']}")

    # Performance
    p = report["performance"]
    print(f"\n📈 Current Performance:")
    print(f"   Accuracy:  {p['accuracy']:.4f} ({p['accuracy']*100:.2f}%)")
    print(f"   Precision: {p['precision']:.4f}")
    print(f"   Recall:    {p['recall']:.4f}")
    print(f"   F1-Score:  {p['f1_score']:.4f}")
    print(f"   ROC-AUC:   {p['roc_auc']:.4f}")

    # Improvement trajectory
    traj = report["improvement_trajectory"]
    if traj:
        print(f"\n📉 Improvement Trajectory ({len(traj)} runs):")
        print(f"   {'Phase':<30} {'Accuracy':>10} {'F1':>10} {'AUC':>10} {'Δ Acc':>10}")
        print(f"   {'-'*30} {'-'*10} {'-'*10} {'-'*10} {'-'*10}")
        for t in traj:
            version = t.get("version", t.get("model", "")[:25])
            delta = f"+{t['delta_accuracy']:.4f}" if t['delta_accuracy'] > 0 else f"{t['delta_accuracy']:.4f}"
            print(f"   {version:<30} {t['accuracy']:>10.4f} {t['f1']:>10.4f} {t['roc_auc']:>10.4f} {delta:>10}")

    # Total improvement
    ti = report.get("total_improvement", {})
    if ti:
        print(f"\n🏆 Total Improvement:")
        print(f"   Accuracy: {ti.get('baseline_accuracy', 0):.4f} → {ti.get('current_accuracy', 0):.4f} "
              f"(+{ti.get('accuracy', 0):.4f})")
        print(f"   F1:       +{ti.get('f1', 0):.4f}")
        print(f"   AUC:      +{ti.get('roc_auc', 0):.4f}")

    # Cross-domain
    cd = report.get("cross_domain", {})
    if cd:
        print(f"\n🌐 Cross-Domain Generalization:")
        print(f"   In-Domain Avg:    {cd.get('in_domain_avg_accuracy', 0):.4f}")
        print(f"   Cross-Domain Avg: {cd.get('cross_domain_avg_accuracy', 0):.4f}")
        ch = cd.get("combined_holdout", {})
        if ch:
            print(f"   Combined Holdout: Acc={ch.get('accuracy', 0):.4f}, "
                  f"F1={ch.get('f1', 0):.4f}, AUC={ch.get('auc', 0):.4f}")
        best = cd.get("best_cross_domain")
        worst = cd.get("worst_cross_domain")
        if best:
            print(f"   Best Pair:  {best['pair']} (Acc: {best['accuracy']:.4f})")
        if worst:
            print(f"   Worst Pair: {worst['pair']} (Acc: {worst['accuracy']:.4f})")

    # Production health
    ph = report.get("production_health", {})
    if ph and ph.get("status") != "NO_DATA":
        print(f"\n🏥 Production Health: {ph['status']}")
        metrics = ph.get("metrics", {})
        print(f"   Predictions (last {ph.get('period_days', 7)}d): {ph.get('total_predictions', 0)}")
        print(f"   Avg Confidence: {metrics.get('avg_confidence', 0):.1f}%")
        print(f"   OOD Rate: {metrics.get('ood_rate', 0):.1%}")
        print(f"   Fake Rate: {metrics.get('fake_rate', 0):.1%}")
        for alert in ph.get("alerts", []):
            icon = "🔴" if alert["severity"] == "critical" else "🟡" if alert["severity"] == "warning" else "✅"
            print(f"   {icon} {alert['message']}")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    report = generate_report()

    if "--json" in sys.argv:
        print(json.dumps(report, indent=2, default=str))
    elif "--save" in sys.argv:
        LOGS_DIR.mkdir(exist_ok=True)
        output_path = LOGS_DIR / "eval_report.json"
        with open(output_path, "w") as f:
            json.dump(report, f, indent=2, default=str)
        print(f"[OK] Report saved to {output_path}")
    else:
        print_report(report)
