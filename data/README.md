# Data Directory

This directory is intentionally empty. Training data is stored in `data_new/` (gitignored due to size).

## Training Data

The model was trained on the **WELFake dataset** containing 59,232 articles:
- `data_new/WELFake_Dataset.csv` — Primary merged dataset (~60MB)
- `data_new/True.csv` — Real news articles
- `data_new/Fake.csv` — Fake news articles

## Obtaining the Data

1. Download the WELFake dataset from [Kaggle](https://www.kaggle.com/datasets/saurabhshahane/fake-news-classification)
2. Place the CSV files in the `data_new/` directory
3. Run `python train.py` to retrain the model
