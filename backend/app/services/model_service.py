# backend/app/services/model_service.py
import os
import sys
import json
import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

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
import redis.asyncio as redis

MODEL_DIR = BASE_BACKEND / "models_store"


class ModelService:
    def __init__(self):
        self._load_meta_and_models()
        self.logger = logging.getLogger(__name__)
        
        # Redis configuration for action queue
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.action_queue_key = os.getenv("ACTION_QUEUE_KEY", "neuroshield:actions")
        
        # Automation policies
        self.automation_policies = {
            "congestion_threshold": 0.6,
            "anomaly_threshold": 0.8,
            "high_utilization_threshold": 0.85,
            "latency_threshold": 50.0
        }

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

    async def _get_redis_connection(self):
        """Get Redis connection for action queue"""
        try:
            return redis.from_url(self.redis_url, decode_responses=True)
        except Exception as e:
            self.logger.error(f"Failed to connect to Redis: {e}")
            return None

    async def enqueue_automation_action(self, device: str, action_type: str, 
                                      parameters: Dict[str, Any], priority: int = 1):
        """Enqueue an automation action to Redis"""
        try:
            r = await self._get_redis_connection()
            if not r:
                return False
            
            action_data = {
                "device": device,
                "action_type": action_type,
                "parameters": parameters,
                "priority": priority,
                "timestamp": pd.Timestamp.now().isoformat(),
                "source": "model_service"
            }
            
            # Use Redis sorted set for priority-based queuing
            score = float(priority) + (pd.Timestamp.now().timestamp() / 1000000)
            await r.zadd(self.action_queue_key, {json.dumps(action_data): score})
            
            self.logger.info(f"Enqueued action: {action_type} for {device}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to enqueue action: {e}")
            return False

    async def evaluate_and_automate(self, device: str, k: int = 120):
        """Evaluate predictions and trigger automation based on policies"""
        try:
            # Get prediction
            prediction = self.predict_for_device(device, k=k)
            if not prediction.get("ok"):
                return prediction
            
            # Get latest metrics for additional context
            df = self.get_last_k_for_device(device, k=1)
            if not df.empty:
                latest = df.iloc[-1]
                utilization = latest.get("Bandwidth Used (MB/s)", 0) / max(latest.get("Bandwidth Allocated (MB/s)", 1), 1)
                latency = latest.get("Latency (ms)", 0)
            else:
                utilization = 0
                latency = 0
            
            # Apply automation policies
            actions_triggered = []
            
            # Congestion policy
            if prediction.get("congestion_prob", 0) > self.automation_policies["congestion_threshold"]:
                action_params = {
                    "congestion_probability": prediction["congestion_prob"],
                    "severity": "high" if prediction["congestion_prob"] > 0.8 else "medium"
                }
                await self.enqueue_automation_action(
                    device, "congestion_mitigation", action_params, priority=2
                )
                actions_triggered.append("congestion_mitigation")
            
            # Anomaly policy
            if prediction.get("anomaly", 0) == 1:
                action_params = {
                    "anomaly_score": 1.0,
                    "detection_method": "isolation_forest"
                }
                await self.enqueue_automation_action(
                    device, "anomaly_investigation", action_params, priority=3
                )
                actions_triggered.append("anomaly_investigation")
            
            # High utilization policy
            if utilization > self.automation_policies["high_utilization_threshold"]:
                action_params = {
                    "utilization": utilization,
                    "current_bandwidth": latest.get("Bandwidth Used (MB/s", 0)
                }
                await self.enqueue_automation_action(
                    device, "bandwidth_optimization", action_params, priority=1
                )
                actions_triggered.append("bandwidth_optimization")
            
            # High latency policy
            if latency > self.automation_policies["latency_threshold"]:
                action_params = {
                    "latency": latency,
                    "threshold": self.automation_policies["latency_threshold"]
                }
                await self.enqueue_automation_action(
                    device, "latency_optimization", action_params, priority=1
                )
                actions_triggered.append("latency_optimization")
            
            # Add automation results to prediction
            prediction["automation_triggered"] = actions_triggered
            prediction["automation_policies"] = self.automation_policies
            
            return prediction
            
        except Exception as e:
            self.logger.error(f"Automation evaluation failed for {device}: {e}")
            return {"device": device, "ok": False, "error": str(e)}

    async def evaluate_all_devices_with_automation(self, k: int = 120):
        """Evaluate all devices and trigger automation policies"""
        devices = self.get_devices()
        results = []
        
        for device in devices:
            try:
                result = await self.evaluate_and_automate(device, k=k)
                results.append(result)
            except Exception as e:
                results.append({
                    "device": device, 
                    "ok": False, 
                    "error": str(e)
                })
        
        return results

    def get_automation_policies(self) -> Dict[str, Any]:
        """Get current automation policies"""
        return self.automation_policies.copy()

    def update_automation_policies(self, new_policies: Dict[str, Any]) -> bool:
        """Update automation policies"""
        try:
            for key, value in new_policies.items():
                if key in self.automation_policies:
                    if key.endswith("_threshold"):
                        self.automation_policies[key] = float(value)
                    else:
                        self.automation_policies[key] = value
            
            self.logger.info(f"Updated automation policies: {new_policies}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to update policies: {e}")
            return False
