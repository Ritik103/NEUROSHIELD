# backend/worker/predictor.py
import os
import time
import json
import joblib
import requests
import redis
from pathlib import Path

HERE = Path(__file__).resolve()
BASE_DIR = HERE.parents[2]
MODEL_DIR = BASE_DIR / "backend" / "models_store"

# Import feature builder
from feature_builder import load_router_logs, engineer_core_features

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
API_URL = os.getenv("API_URL", "http://localhost:8000")
ACTION_TTL = int(os.getenv("ACTION_LOCK_TTL", "900"))

r = redis.from_url(REDIS_URL)

# Load models/meta
meta = json.loads((MODEL_DIR / "meta.json").read_text())
clf = joblib.load(MODEL_DIR / "congestion_clf.joblib")
iso = joblib.load(MODEL_DIR / "anomaly_iso.joblib")
threshold = float(meta.get("threshold", 0.6))
feature_cols = list(meta.get("feature_cols", []))

def align_row(x_row):
    import pandas as pd
    aligned = pd.DataFrame(0, index=[0], columns=feature_cols)
    for c in x_row.index:
        if c in aligned.columns:
            aligned.at[0, c] = x_row[c]
    return aligned.fillna(0).astype(float)

def get_devices():
    df = load_router_logs()
    if df is None or df.empty:
        return []
    return sorted(df["Device Name"].dropna().unique().tolist())

def get_last_k_for_device(device, k=120):
    df = load_router_logs()
    if df is None or df.empty:
        return df
    df_dev = df[df["Device Name"] == device].copy()
    if df_dev.empty:
        return df_dev
    df_dev["Timestamp"] = pd.to_datetime(df_dev["Timestamp"], errors="coerce")
    df_dev = df_dev.sort_values("Timestamp").reset_index(drop=True)
    return df_dev.tail(int(k)).sort_values("Timestamp").reset_index(drop=True)

def main_loop():
    print("Predictor started, press Ctrl+C to stop.")
    while True:
        try:
            devices = get_devices()
            for dev in devices:
                df = get_last_k_for_device(dev, k=120)
                if df.empty or len(df) < 10:
                    continue
                X_all, y_all, ts_df, _ = engineer_core_features(df)
                x_last = X_all.iloc[[-1]]
                x_aligned = align_row(x_last.iloc[0])
                prob = float(clf.predict_proba(x_aligned)[:, 1][0])
                anom = int(iso.predict(x_aligned)[0] == -1)

                lock_key = f"is_action_active:{dev}"
                locked = r.get(lock_key)

                print(f"[{dev}] p_congest={prob:.3f} anomaly={anom} locked={bool(locked)}")

                if (prob >= threshold or anom) and not locked:
                    payload = {"device": dev, "action": "apply_qos_policy", "params": {"policy": "limit_low_priority_20pct"}}
                    try:
                        requests.post(f"{API_URL}/api/actions", json=payload, timeout=3)
                    except Exception as e:
                        print("Action call failed:", e)
                    r.setex(lock_key, ACTION_TTL, "1")
            time.sleep(60)  # loop interval
        except KeyboardInterrupt:
            print("Predictor stopped by user.")
            break
        except Exception as e:
            print("Predictor loop error:", e)
            time.sleep(5)

if __name__ == "__main__":
    main_loop()
