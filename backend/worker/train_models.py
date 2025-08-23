from pathlib import Path
import json, joblib
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix

from feature_builder import load_router_logs, engineer_core_features, train_test_split_time

# Resolve paths correctly
HERE = Path(__file__).resolve()
BASE_DIR = HERE.parents[2]   # .../NEUROSHIELD
MODEL_DIR = BASE_DIR / "backend" / "models_store"
MODEL_DIR.mkdir(parents=True, exist_ok=True)

def main():
    # 1. Load router logs
    df = load_router_logs()
    X, y, ts_df, meta = engineer_core_features(df)

    # 2. Time-based split
    (Xtr, ytr), (Xte, yte) = train_test_split_time(X, y, ts_df["Timestamp"], test_frac=0.2)

    # 3. Baseline Logistic Regression
    clf = Pipeline([
        ("scaler", StandardScaler(with_mean=False)),  # sparse-safe if needed
        ("model", LogisticRegression(max_iter=1000))
    ])
    clf.fit(Xtr, ytr)
    yhat = clf.predict(Xte)
    yproba = clf.predict_proba(Xte)[:, 1]

    print("=== Logistic Regression ===")
    print(classification_report(yte, yhat, digits=3))
    print("Confusion:\n", confusion_matrix(yte, yhat))

    # 4. Stronger model: Random Forest
    rf = RandomForestClassifier(
        n_estimators=200,
        random_state=42,
        class_weight="balanced"
    )
    rf.fit(Xtr, ytr)
    yhat_rf = rf.predict(Xte)
    print("=== RandomForest ===")
    print(classification_report(yte, yhat_rf, digits=3))
    print("Confusion:\n", confusion_matrix(yte, yhat_rf))

    # 5. Anomaly detector (assume mostly normal in training)
    iso = IsolationForest(
        n_estimators=200,
        contamination=0.05,
        random_state=42
    )
    iso.fit(Xtr)

    # 6. Save artifacts
    joblib.dump(clf, MODEL_DIR / "congestion_clf.joblib")
    joblib.dump(iso, MODEL_DIR / "anomaly_iso.joblib")

    meta.update({
        "feature_cols": list(X.columns),
        "label_name": "Congestion_Label",
        "threshold": 0.6,   # default action threshold
        "model": "logreg",  # or "rf"
    })
    (MODEL_DIR / "meta.json").write_text(json.dumps(meta, indent=2))

    print(f"✅ Models saved to {MODEL_DIR}")

if __name__ == "__main__":
    main()
