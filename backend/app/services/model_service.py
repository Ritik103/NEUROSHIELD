# backend/app/services/model_service.py
import os
import sys
import json
from pathlib import Path

# Add worker dir so we can reuse feature_builder
HERE = Path(__file__).resolve()
BASE_BACKEND = HERE.parents[2]   # .../NEUROSHIELD/backend
WORKER_DIR = BASE_BACKEND / "worker"
if str(WORKER_DIR) not in sys.path:
    sys.path.insert(0, str(WORKER_DIR))

# Now import the feature builder helpers (these are the canonical loader + fe builder)
from feature_builder import load_router_logs, engineer_core_features

import joblib
import pandas as pd
import sqlite3

MODEL_DIR = BASE_BACKEND / "models_store"


class ModelService:
    def __init__(self):
        self._load_meta_and_models()

    def _load_meta_and_models(self):
        meta_path = MODEL_DIR / "meta.json"
        if not meta_path.exists():
            raise FileNotFoundError(f"meta.json not found in {MODEL_DIR}. Run training first.")
        self.meta = json.loads(meta_path.read_text())

        clf_path = MODEL_DIR / "congestion_clf.joblib"
        iso_path = MODEL_DIR / "anomaly_iso.joblib"
        if not clf_path.exists() or not iso_path.exists():
            raise FileNotFoundError("Model artifacts missing. Run training first.")
        self.clf = joblib.load(clf_path)
        self.iso = joblib.load(iso_path)

        self.feature_cols = list(self.meta.get("feature_cols", []))
        self.threshold = float(self.meta.get("threshold", 0.6))

    def get_devices(self):
        """
        Return list of distinct devices using the canonical loader (works for DB or CSV).
        """
        df = load_router_logs()
        if df is None or df.empty:
            return []
        # Column produced by loader is "Device Name"
        return sorted(df["Device Name"].dropna().unique().tolist())

    def get_last_k_for_device(self, device, k=120):
        """
        Return last k rows for a device as a pandas DataFrame, sorted ascending by Timestamp.
        Uses canonical loader so column names are normalized.
        """
        df = load_router_logs()
        if df is None or df.empty:
            return pd.DataFrame()
        # Filter by canonical column
        df_dev = df[df["Device Name"] == device].copy()
        if df_dev.empty:
            return pd.DataFrame()
        # Ensure Timestamp parsed and sort
        df_dev["Timestamp"] = pd.to_datetime(df_dev["Timestamp"], errors="coerce")
        df_dev = df_dev.sort_values("Timestamp").reset_index(drop=True)
        # take last k (most recent) and return sorted ascending
        df_tail = df_dev.tail(int(k)).sort_values("Timestamp").reset_index(drop=True)
        return df_tail

    def _align_with_meta(self, X_row):
        """
        Align single-row Series/DataFrame X_row with saved feature columns.
        Returns a 1-row DataFrame with columns in the same order as model training.
        """
        # Create DataFrame with proper float dtype from the start
        aligned = pd.DataFrame(0.0, index=[0], columns=self.feature_cols, dtype=float)
        # If X_row is Series, iterate index; if DataFrame row, use its columns
        for c in X_row.index:
            if c in aligned.columns:
                # Ensure proper type conversion
                value = X_row[c]
                if isinstance(value, str) and value.lower() in ['true', 'false']:
                    value = float(value.lower() == 'true')
                else:
                    try:
                        value = float(value)
                    except (ValueError, TypeError):
                        value = 0.0
                aligned.at[0, c] = value
        # Fill any remaining NaN values and ensure float type
        aligned = aligned.fillna(0.0)
        return aligned

    def predict_for_device(self, device, k=120):
        """
        Build features for the device, align with model, return probability/prediction/anomaly.
        """
        df = self.get_last_k_for_device(device, k=int(k))
        if df.empty or len(df) < 3:
            return {"device": device, "ok": False, "reason": "not enough data", "rows": len(df)}

        # Build features using canonical function
        X_all, y_all, ts_df, _ = engineer_core_features(df)
        if X_all.empty:
            return {"device": device, "ok": False, "reason": "no features after engineering"}

        x_last = X_all.iloc[-1]
        x_aligned = self._align_with_meta(x_last)

        try:
            prob = float(self.clf.predict_proba(x_aligned)[:, 1][0])
            pred = int(self.clf.predict(x_aligned)[0])
        except Exception:
            # fallback if predict_proba is not available
            pred = int(self.clf.predict(x_aligned)[0])
            prob = float(pred)

        try:
            anom_val = int(self.iso.predict(x_aligned)[0] == -1)
        except Exception:
            anom_val = 0

        return {
            "device": device,
            "ok": True,
            "last_timestamp": str(ts_df["Timestamp"].iloc[-1]) if not ts_df.empty else None,
            "congestion_prob": prob,
            "congestion_pred": int(pred),
            "anomaly": anom_val,
            "threshold": self.threshold,
            "model": self.meta.get("model", "logreg")
        }

    def predict_all_devices(self, k=120):
        devices = self.get_devices()
        results = []
        for d in devices:
            try:
                res = self.predict_for_device(d, k=k)
            except Exception as e:
                res = {"device": d, "ok": False, "error": str(e)}
            results.append(res)
        return results
