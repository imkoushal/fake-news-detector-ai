import joblib
import sys
from app.utils import clean_text

# Fix for pickle (__main__ reference issue)
sys.modules["__main__"].clean_text = clean_text

model = joblib.load("models/pipeline_svm.joblib")

def analyze_article(text: str):
    prediction = model.predict([text])[0]
    label = "FAKE" if prediction == 1 else "REAL"

    return {
        "prediction": label
    }