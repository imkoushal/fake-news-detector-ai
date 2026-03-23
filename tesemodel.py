from utils import clean_text
import joblib

data = joblib.load("models/pipeline_svm.joblib")

print("Type:", type(data))

if isinstance(data, dict):
    print("Keys:", data.keys())
    model = data.get("model") or data.get("classifier")
else:
    model = data

text = ["Breaking news: Scientists discover miracle cure!"]

prediction = model.predict(text)[0]

label = "FAKE" if prediction == 1 else "REAL"

print("Prediction:", label)
print("Prediction:", model.predict(text))