# backend/app/services/db.py
import sqlite3
import os
import asyncio
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import pandas as pd
import logging

logger = logging.getLogger(__name__)

class DatabaseService:
    def __init__(self, db_path: str = None):
        if db_path is None:
            # Default to backend directory
            backend_dir = Path(__file__).parent.parent.parent
            self.db_path = str(backend_dir / "metrics.db")
        else:
            self.db_path = db_path
        
        self._init_database()

    def _init_database(self):
        """Initialize database with all required tables"""
        conn = sqlite3.connect(self.db_path)
        try:
            # Router logs table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS router_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    device_name TEXT NOT NULL,
                    source_ip TEXT,
                    destination_ip TEXT,
                    traffic_volume REAL,
                    latency REAL,
                    bandwidth_allocated REAL,
                    bandwidth_used REAL,
                    congestion_flag TEXT,
                    log_text TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Predictions table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS predictions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_name TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    congestion_prob REAL,
                    congestion_pred INTEGER,
                    anomaly_score INTEGER,
                    model_version TEXT,
                    features_json TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Actions log table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS actions_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    device_name TEXT NOT NULL,
                    action_type TEXT NOT NULL,
                    parameters_json TEXT,
                    status TEXT DEFAULT 'queued',
                    result_json TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    executed_at TEXT
                )
            """)

            # Events table for broadcaster
            conn.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT UNIQUE,
                    event_type TEXT NOT NULL,
                    device_name TEXT,
                    priority INTEGER,
                    data_json TEXT,
                    timestamp TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Device status table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS device_status (
                    device_name TEXT PRIMARY KEY,
                    last_seen TEXT,
                    status TEXT DEFAULT 'unknown',
                    last_metrics_json TEXT,
                    last_prediction_json TEXT,
                    alerts_count INTEGER DEFAULT 0,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Metrics aggregation table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS metrics_hourly (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_name TEXT NOT NULL,
                    hour_timestamp TEXT NOT NULL,
                    avg_traffic_volume REAL,
                    avg_latency REAL,
                    avg_bandwidth_used REAL,
                    max_bandwidth_used REAL,
                    congestion_events INTEGER DEFAULT 0,
                    anomaly_events INTEGER DEFAULT 0,
                    total_records INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(device_name, hour_timestamp)
                )
            """)

            # Create indexes for better performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_router_logs_device_time ON router_logs(device_name, timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_predictions_device_time ON predictions(device_name, timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_actions_device_time ON actions_log(device_name, timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_device_time ON events(device_name, timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_metrics_hourly_device_time ON metrics_hourly(device_name, hour_timestamp)")

            conn.commit()
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            raise
        finally:
            conn.close()

    def get_connection(self):
        """Get a database connection"""
        return sqlite3.connect(self.db_path, check_same_thread=False)

    # Router logs methods
    def insert_router_log(self, log_data: Dict[str, Any]) -> int:
        """Insert a router log entry"""
        conn = self.get_connection()
        try:
            cursor = conn.execute("""
                INSERT INTO router_logs 
                (timestamp, device_name, source_ip, destination_ip, traffic_volume, 
                 latency, bandwidth_allocated, bandwidth_used, congestion_flag, log_text)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                log_data.get('Timestamp'),
                log_data.get('Device Name'),
                log_data.get('Source IP'),
                log_data.get('Destination IP'),
                log_data.get('Traffic Volume (MB/s)'),
                log_data.get('Latency (ms)'),
                log_data.get('Bandwidth Allocated (MB/s)'),
                log_data.get('Bandwidth Used (MB/s)'),
                log_data.get('Congestion Flag'),
                log_data.get('Log Text')
            ))
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def batch_insert_router_logs(self, logs: List[Dict[str, Any]]) -> int:
        """Batch insert router logs"""
        conn = self.get_connection()
        try:
            data = []
            for log in logs:
                data.append((
                    log.get('Timestamp'),
                    log.get('Device Name'),
                    log.get('Source IP'),
                    log.get('Destination IP'),
                    log.get('Traffic Volume (MB/s)'),
                    log.get('Latency (ms)'),
                    log.get('Bandwidth Allocated (MB/s)'),
                    log.get('Bandwidth Used (MB/s)'),
                    log.get('Congestion Flag'),
                    log.get('Log Text')
                ))
            
            conn.executemany("""
                INSERT INTO router_logs 
                (timestamp, device_name, source_ip, destination_ip, traffic_volume, 
                 latency, bandwidth_allocated, bandwidth_used, congestion_flag, log_text)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, data)
            conn.commit()
            return len(data)
        finally:
            conn.close()

    def get_router_logs(self, device_name: str = None, limit: int = None, 
                       start_time: str = None, end_time: str = None) -> pd.DataFrame:
        """Get router logs with optional filtering"""
        conn = self.get_connection()
        try:
            query = "SELECT * FROM router_logs WHERE 1=1"
            params = []
            
            if device_name:
                query += " AND device_name = ?"
                params.append(device_name)
            
            if start_time:
                query += " AND timestamp >= ?"
                params.append(start_time)
            
            if end_time:
                query += " AND timestamp <= ?"
                params.append(end_time)
            
            query += " ORDER BY timestamp DESC"
            
            if limit:
                query += f" LIMIT {int(limit)}"
            
            return pd.read_sql_query(query, conn, params=params)
        finally:
            conn.close()

    # Predictions methods
    def insert_prediction(self, device_name: str, timestamp: str, prediction_data: Dict[str, Any]) -> int:
        """Insert a prediction result"""
        conn = self.get_connection()
        try:
            cursor = conn.execute("""
                INSERT INTO predictions 
                (device_name, timestamp, congestion_prob, congestion_pred, anomaly_score, 
                 model_version, features_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                device_name,
                timestamp,
                prediction_data.get('congestion_prob'),
                prediction_data.get('congestion_pred'),
                prediction_data.get('anomaly'),
                prediction_data.get('model'),
                json.dumps(prediction_data.get('features', {}))
            ))
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def get_predictions(self, device_name: str = None, limit: int = 100) -> pd.DataFrame:
        """Get prediction history"""
        conn = self.get_connection()
        try:
            query = "SELECT * FROM predictions WHERE 1=1"
            params = []
            
            if device_name:
                query += " AND device_name = ?"
                params.append(device_name)
            
            query += " ORDER BY timestamp DESC"
            
            if limit:
                query += f" LIMIT {int(limit)}"
            
            return pd.read_sql_query(query, conn, params=params)
        finally:
            conn.close()

    # Actions methods
    def insert_action(self, device_name: str, action_type: str, parameters: Dict[str, Any]) -> int:
        """Insert an action to be executed"""
        conn = self.get_connection()
        try:
            cursor = conn.execute("""
                INSERT INTO actions_log 
                (timestamp, device_name, action_type, parameters_json)
                VALUES (?, ?, ?, ?)
            """, (
                datetime.now().isoformat(),
                device_name,
                action_type,
                json.dumps(parameters)
            ))
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def update_action_result(self, action_id: int, status: str, result: Dict[str, Any]):
        """Update action execution result"""
        conn = self.get_connection()
        try:
            conn.execute("""
                UPDATE actions_log 
                SET status = ?, result_json = ?, executed_at = ?
                WHERE id = ?
            """, (status, json.dumps(result), datetime.now().isoformat(), action_id))
            conn.commit()
        finally:
            conn.close()

    def get_pending_actions(self) -> List[Dict[str, Any]]:
        """Get pending actions to execute"""
        conn = self.get_connection()
        try:
            cursor = conn.execute("""
                SELECT id, device_name, action_type, parameters_json, timestamp
                FROM actions_log 
                WHERE status = 'queued'
                ORDER BY timestamp ASC
            """)
            
            actions = []
            for row in cursor.fetchall():
                actions.append({
                    'id': row[0],
                    'device_name': row[1],
                    'action_type': row[2],
                    'parameters': json.loads(row[3]),
                    'timestamp': row[4]
                })
            return actions
        finally:
            conn.close()

    # Device status methods
    def update_device_status(self, device_name: str, status: str, 
                           metrics: Dict[str, Any] = None, prediction: Dict[str, Any] = None):
        """Update device status"""
        conn = self.get_connection()
        try:
            conn.execute("""
                INSERT OR REPLACE INTO device_status 
                (device_name, last_seen, status, last_metrics_json, last_prediction_json, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                device_name,
                datetime.now().isoformat(),
                status,
                json.dumps(metrics) if metrics else None,
                json.dumps(prediction) if prediction else None,
                datetime.now().isoformat()
            ))
            conn.commit()
        finally:
            conn.close()

    def get_device_status(self, device_name: str = None) -> List[Dict[str, Any]]:
        """Get device status"""
        conn = self.get_connection()
        try:
            if device_name:
                cursor = conn.execute("""
                    SELECT * FROM device_status WHERE device_name = ?
                """, (device_name,))
            else:
                cursor = conn.execute("SELECT * FROM device_status")
            
            columns = [desc[0] for desc in cursor.description]
            devices = []
            for row in cursor.fetchall():
                device_data = dict(zip(columns, row))
                if device_data['last_metrics_json']:
                    device_data['last_metrics'] = json.loads(device_data['last_metrics_json'])
                if device_data['last_prediction_json']:
                    device_data['last_prediction'] = json.loads(device_data['last_prediction_json'])
                devices.append(device_data)
            return devices
        finally:
            conn.close()

    # Metrics aggregation methods
    def update_hourly_metrics(self, device_name: str, hour_timestamp: str, metrics: Dict[str, Any]):
        """Update hourly aggregated metrics"""
        conn = self.get_connection()
        try:
            conn.execute("""
                INSERT OR REPLACE INTO metrics_hourly 
                (device_name, hour_timestamp, avg_traffic_volume, avg_latency, 
                 avg_bandwidth_used, max_bandwidth_used, congestion_events, 
                 anomaly_events, total_records)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                device_name,
                hour_timestamp,
                metrics.get('avg_traffic_volume'),
                metrics.get('avg_latency'),
                metrics.get('avg_bandwidth_used'),
                metrics.get('max_bandwidth_used'),
                metrics.get('congestion_events', 0),
                metrics.get('anomaly_events', 0),
                metrics.get('total_records', 0)
            ))
            conn.commit()
        finally:
            conn.close()

    def get_hourly_metrics(self, device_name: str = None, hours: int = 24) -> pd.DataFrame:
        """Get hourly aggregated metrics"""
        conn = self.get_connection()
        try:
            cutoff_time = (datetime.now() - timedelta(hours=hours)).isoformat()
            
            query = """
                SELECT * FROM metrics_hourly 
                WHERE hour_timestamp >= ?
            """
            params = [cutoff_time]
            
            if device_name:
                query += " AND device_name = ?"
                params.append(device_name)
            
            query += " ORDER BY hour_timestamp DESC"
            
            return pd.read_sql_query(query, conn, params=params)
        finally:
            conn.close()

    # Events methods
    def insert_event(self, event_id: str, event_type: str, device_name: str, 
                    priority: int, data: Dict[str, Any], timestamp: str):
        """Insert an event"""
        conn = self.get_connection()
        try:
            conn.execute("""
                INSERT OR REPLACE INTO events 
                (event_id, event_type, device_name, priority, data_json, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (event_id, event_type, device_name, priority, json.dumps(data), timestamp))
            conn.commit()
        finally:
            conn.close()

    def get_recent_events(self, limit: int = 50, event_type: str = None, 
                         device_name: str = None) -> List[Dict[str, Any]]:
        """Get recent events"""
        conn = self.get_connection()
        try:
            query = "SELECT * FROM events WHERE 1=1"
            params = []
            
            if event_type:
                query += " AND event_type = ?"
                params.append(event_type)
            
            if device_name:
                query += " AND device_name = ?"
                params.append(device_name)
            
            query += " ORDER BY timestamp DESC"
            
            if limit:
                query += f" LIMIT {int(limit)}"
            
            cursor = conn.execute(query, params)
            columns = [desc[0] for desc in cursor.description]
            events = []
            for row in cursor.fetchall():
                event_data = dict(zip(columns, row))
                event_data['data'] = json.loads(event_data['data_json'])
                events.append(event_data)
            return events
        finally:
            conn.close()

    # Utility methods
    def cleanup_old_data(self, days_to_keep: int = 30):
        """Clean up old data to prevent database bloat"""
        cutoff_date = (datetime.now() - timedelta(days=days_to_keep)).isoformat()
        
        conn = self.get_connection()
        try:
            # Clean up old router logs
            conn.execute("DELETE FROM router_logs WHERE timestamp < ?", (cutoff_date,))
            
            # Clean up old predictions
            conn.execute("DELETE FROM predictions WHERE timestamp < ?", (cutoff_date,))
            
            # Clean up old events
            conn.execute("DELETE FROM events WHERE timestamp < ?", (cutoff_date,))
            
            # Clean up old actions (keep completed ones for audit)
            conn.execute("""
                DELETE FROM actions_log 
                WHERE timestamp < ? AND status IN ('completed', 'failed')
            """, (cutoff_date,))
            
            conn.commit()
            logger.info(f"Cleaned up data older than {days_to_keep} days")
        finally:
            conn.close()

    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        conn = self.get_connection()
        try:
            stats = {}
            
            # Count records in each table
            tables = ['router_logs', 'predictions', 'actions_log', 'events', 'device_status', 'metrics_hourly']
            for table in tables:
                cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")
                stats[f"{table}_count"] = cursor.fetchone()[0]
            
            # Database file size
            db_file = Path(self.db_path)
            if db_file.exists():
                stats['db_size_mb'] = round(db_file.stat().st_size / 1024 / 1024, 2)
            
            return stats
        finally:
            conn.close()

# Global database service instance
db_service = DatabaseService()
