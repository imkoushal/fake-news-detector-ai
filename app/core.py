import re
import joblib

# =============================================================================
# CONFIG
# =============================================================================
UNCERTAINTY_THRESHOLD = 0.1   # |p_real - p_fake| < this → UNCERTAIN
MIN_WORDS = 5                 # fewer words → UNCERTAIN


# =============================================================================
# Same gentle clean_text used during training
# =============================================================================
def clean_text(text: str) -> str:
    text = str(text).lower()
    text = re.sub(r"http\S+|www\.\S+", " ", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"@\w+", " ", text)
    text = re.sub(r"[^a-z\s']", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


# =============================================================================
# Load pipeline once at import time
# =============================================================================
model = joblib.load("models/pipeline_svm.joblib")


def analyze_article(text: str) -> dict:
    """
    Clean text → predict → return prediction + confidence.
    Label mapping:  0 = FAKE,  1 = REAL
    Returns UNCERTAIN when confidence gap is too small or input too short.
    """
    cleaned = clean_text(text)

    # --- Input too short ---
    if len(cleaned.split()) < MIN_WORDS:
        print(f"[DEBUG] TOO SHORT  input='{text[:80]}'  words={len(cleaned.split())}")
        return {
            "prediction": "UNCERTAIN",
            "confidence": 0.0,
        }

    # --- Predict ---
    proba = model.predict_proba([cleaned])[0]   # [p_fake, p_real]
    p_fake, p_real = float(proba[0]), float(proba[1])
    diff = abs(p_real - p_fake)

    # --- Uncertainty check ---
    if diff < UNCERTAINTY_THRESHOLD:
        label = "UNCERTAIN"
        confidence = round(max(p_fake, p_real), 4)
        print(f"[DEBUG] UNCERTAIN  p_fake={p_fake:.3f}  p_real={p_real:.3f}  diff={diff:.3f}")
    else:
        pred = 1 if p_real > p_fake else 0
        label = "REAL" if pred == 1 else "FAKE"
        confidence = round(float(proba[pred]), 4)
        print(f"[DEBUG] {label}  conf={confidence:.3f}  p_fake={p_fake:.3f}  p_real={p_real:.3f}")

    return {
        "prediction": label,
        "confidence": confidence,
    }