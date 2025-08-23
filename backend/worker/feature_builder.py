import os
from pathlib import Path
import pandas as pd
import numpy as np

# Resolve project root and data paths robustly
HERE = Path(__file__).resolve()
BASE_DIR = HERE.parents[2]  # .../NEUROSHIELD
DATA_DIR = BASE_DIR / "datasets"
DB_PATH = os.getenv("DB_PATH", str((BASE_DIR / "backend" / "metrics.db").resolve()))

NUMERIC_COLS = [
    "Traffic Volume (MB/s)", "Latency (ms)",
    "Bandwidth Allocated (MB/s)", "Bandwidth Used (MB/s)"
]

def load_router_logs(limit=None):
    import sqlite3
    
    # Try to load from database first
    try:
        conn = sqlite3.connect(DB_PATH)
        # Check if table exists and has data
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='router_logs'")
        if cursor.fetchone():
            cursor.execute("SELECT COUNT(*) FROM router_logs")
            count = cursor.fetchone()[0]
            if count > 0:
                q = "SELECT timestamp as 'Timestamp', device_name as 'Device Name', source_ip as 'Source IP', destination_ip as 'Destination IP', traffic_volume as 'Traffic Volume (MB/s)', latency as 'Latency (ms)', bandwidth_allocated as 'Bandwidth Allocated (MB/s)', bandwidth_used as 'Bandwidth Used (MB/s)', congestion_flag as 'Congestion Flag', log_text as 'Log Text' FROM router_logs ORDER BY id ASC"
                if limit:
                    q += f" LIMIT {int(limit)}"
                df = pd.read_sql_query(q, conn)
                conn.close()
                # Continue with existing processing
                cols = (
                    df.columns.astype(str)
                    .str.strip()
                    .str.replace(r"[_\s]+", " ", regex=True)   # underscores -> spaces
                    .str.replace(r"\s*\(mb/s\)\s*", " mb/s", regex=True)
                    .str.replace(r"\s*\(ms\)\s*", " ms", regex=True)
                    .str.replace(r"\s+", " ", regex=True)
                )
                df.columns = cols
                # Continue with column mapping and rest of processing...
                col_map = {}
                for c in df.columns:
                    cl = c.lower()
                    if "timestamp" in cl:
                        col_map[c] = "Timestamp"
                    elif "device" in cl and "name" in cl:
                        col_map[c] = "Device Name"
                    elif "source" in cl and "ip" in cl:
                        col_map[c] = "Source IP"
                    elif "destination" in cl and "ip" in cl:
                        col_map[c] = "Destination IP"
                    elif "traffic" in cl and "mb" in cl:
                        col_map[c] = "Traffic Volume (MB/s)"
                    elif ("latency" in cl) or ("ms" in cl and "lat" in cl):
                        col_map[c] = "Latency (ms)"
                    elif "bandwidth" in cl and "allocated" in cl:
                        col_map[c] = "Bandwidth Allocated (MB/s)"
                    elif "bandwidth" in cl and ("used" in cl or "util" in cl):
                        col_map[c] = "Bandwidth Used (MB/s)"
                    elif "congestion" in cl:
                        col_map[c] = "Congestion Flag"
                    elif "log" in cl or "text" in cl:
                        col_map[c] = "Log Text"
                    else:
                        col_map[c] = c

                df = df.rename(columns=col_map)
                expected = [
                    "Timestamp", "Device Name", "Source IP", "Destination IP",
                    "Traffic Volume (MB/s)", "Latency (ms)",
                    "Bandwidth Allocated (MB/s)", "Bandwidth Used (MB/s)",
                    "Congestion Flag", "Log Text"
                ]
                for e in expected:
                    if e not in df.columns:
                        df[e] = pd.NA

                df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors="coerce")
                df = df.sort_values(["Device Name", "Timestamp"]).reset_index(drop=True)
                return df
        conn.close()
    except Exception as e:
        print(f"Database loading failed, falling back to CSV: {e}")
    
    # Fallback: Load from CSV files and populate database
    csv_files = [
        DATA_DIR / "Router_A_router_log_15_days.csv",
        DATA_DIR / "Router_B_router_log_15_days.csv", 
        DATA_DIR / "Router_C_router_log_15_days.csv"
    ]
    
    dfs = []
    for csv_file in csv_files:
        if csv_file.exists():
            try:
                df_temp = pd.read_csv(csv_file)
                dfs.append(df_temp)
                print(f"Loaded {len(df_temp)} records from {csv_file.name}")
            except Exception as e:
                print(f"Error loading {csv_file}: {e}")
    
    if not dfs:
        print("No CSV files found, returning empty DataFrame")
        return pd.DataFrame()
    
    # Combine all CSV data
    df = pd.concat(dfs, ignore_index=True)
    print(f"Combined total: {len(df)} records from {len(dfs)} routers")
    
    # Populate database for future use
    try:
        conn = sqlite3.connect(DB_PATH)
        # Create table if not exists
        conn.execute("""
            CREATE TABLE IF NOT EXISTS router_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                device_name TEXT,
                source_ip TEXT,
                destination_ip TEXT,
                traffic_volume REAL,
                latency REAL,
                bandwidth_allocated REAL,
                bandwidth_used REAL,
                congestion_flag TEXT,
                log_text TEXT
            )
        """)
        
        # Clear existing data and insert new
        conn.execute("DELETE FROM router_logs")
        
        # Map CSV columns to database columns
        db_df = df.copy()
        column_mapping = {
            'Timestamp': 'timestamp',
            'Device Name': 'device_name',
            'Source IP': 'source_ip',
            'Destination IP': 'destination_ip',
            'Traffic Volume (MB/s)': 'traffic_volume',
            'Latency (ms)': 'latency',
            'Bandwidth Allocated (MB/s)': 'bandwidth_allocated',
            'Bandwidth Used (MB/s)': 'bandwidth_used',
            'Congestion Flag': 'congestion_flag',
            'Log Text': 'log_text'
        }
        
        # Rename columns for database insertion
        db_df = db_df.rename(columns=column_mapping)
        
        # Insert into database
        db_df.to_sql('router_logs', conn, if_exists='append', index=False)
        conn.commit()
        conn.close()
        print(f"Populated database with {len(df)} records")
    except Exception as e:
        print(f"Database population failed: {e}")
    
    # Apply limit if specified
    if limit:
        df = df.head(int(limit))

    # 1) Normalize column names: strip, collapse whitespace/underscores, lower
    cols = (
        df.columns.astype(str)
        .str.strip()
        .str.replace(r"[_\s]+", " ", regex=True)   # underscores -> spaces
        .str.replace(r"\s*\(mb/s\)\s*", " mb/s", regex=True)
        .str.replace(r"\s*\(ms\)\s*", " ms", regex=True)
        .str.replace(r"\s+", " ", regex=True)
    )
    df.columns = cols

    # 2) Map cleaned names to canonical names expected by feature code
    # Build lower->canonical map for flexible matching
    col_map = {}
    for c in df.columns:
        cl = c.lower()
        if "timestamp" in cl:
            col_map[c] = "Timestamp"
        elif "device" in cl and "name" in cl:
            col_map[c] = "Device Name"
        elif "source" in cl and "ip" in cl:
            col_map[c] = "Source IP"
        elif "destination" in cl and "ip" in cl:
            col_map[c] = "Destination IP"
        elif "traffic" in cl and "mb" in cl:
            col_map[c] = "Traffic Volume (MB/s)"
        elif ("latency" in cl) or ("ms" in cl and "lat" in cl):
            col_map[c] = "Latency (ms)"
        elif "bandwidth" in cl and "allocated" in cl:
            col_map[c] = "Bandwidth Allocated (MB/s)"
        elif "bandwidth" in cl and ("used" in cl or "util" in cl):
            col_map[c] = "Bandwidth Used (MB/s)"
        elif "congestion" in cl:
            col_map[c] = "Congestion Flag"
        elif "log" in cl or "text" in cl:
            col_map[c] = "Log Text"
        else:
            # keep original if unsure
            col_map[c] = c

    df = df.rename(columns=col_map)

    # Final sanity: strip again and ensure expected columns exist (add missing as NaN)
    expected = [
        "Timestamp", "Device Name", "Source IP", "Destination IP",
        "Traffic Volume (MB/s)", "Latency (ms)",
        "Bandwidth Allocated (MB/s)", "Bandwidth Used (MB/s)",
        "Congestion Flag", "Log Text"
    ]
    for e in expected:
        if e not in df.columns:
            df[e] = pd.NA

    # Normalize types & sorting
    df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors="coerce")
    df = df.sort_values(["Device Name", "Timestamp"]).reset_index(drop=True)
    return df


def _safe_roll(g, col, w):
    return g[col].rolling(window=w, min_periods=max(1, w//2)).mean()

def engineer_core_features(df: pd.DataFrame):
    df = df.copy()

    # Ensure numeric columns are float
    for col in [
        "Traffic Volume (MB/s)",
        "Latency (ms)",
        "Bandwidth Allocated (MB/s)",
        "Bandwidth Used (MB/s)"
    ]:

        df[col] = pd.to_numeric(df[col], errors="coerce")


    # 🔑 Ensure no stray spaces in columns
    df.columns = df.columns.str.strip()

    # Basic
    df["utilization"] = df["Bandwidth Used (MB/s)"] / df["Bandwidth Allocated (MB/s)"].replace(0, np.nan)
    df["utilization"] = df["utilization"].fillna(0).clip(0, 5)

    # Time features
    df["hour_of_day"] = df["Timestamp"].dt.hour
    df["day_of_week"] = df["Timestamp"].dt.dayofweek
    df["is_weekend"] = (df["day_of_week"] >= 5).astype(int)

    # Deltas & rollings per device
    df = df.sort_values(["Device Name", "Timestamp"])
    g = df.groupby("Device Name", group_keys=False)

    for col in ["Bandwidth Used (MB/s)", "Latency (ms)", "Traffic Volume (MB/s)"]:
        df[f"{col}_diff1"] = g[col].diff().fillna(0)
        for w in (5, 15, 60):
            df[f"{col}_ma{w}"] = _safe_roll(g, col, w).reset_index(drop=True)

    df["Congestion_Label"] = (df["Congestion Flag"].str.upper() == "YES").astype(int)

    # Select feature columns
    feat_cols = [
        "utilization","hour_of_day","day_of_week","is_weekend",
        "Bandwidth Used (MB/s)_diff1","Latency (ms)_diff1","Traffic Volume (MB/s)_diff1",
        "Bandwidth Used (MB/s)_ma5","Bandwidth Used (MB/s)_ma15","Bandwidth Used (MB/s)_ma60",
        "Latency (ms)_ma5","Latency (ms)_ma15","Latency (ms)_ma60",
        "Traffic Volume (MB/s)_ma5","Traffic Volume (MB/s)_ma15","Traffic Volume (MB/s)_ma60",
    ]

    # One-hot device
    df = pd.get_dummies(df, columns=["Device Name"], drop_first=False)
    device_cols = [c for c in df.columns if c.startswith("Device Name_")]

    X = df[feat_cols + device_cols].fillna(0)
    y = df["Congestion_Label"].astype(int)
    meta = {"feature_cols": feat_cols + device_cols, "device_cols": device_cols}
    return X, y, df[["Timestamp"] + [c for c in df.columns if c.startswith("Device Name_")] ], meta

def train_test_split_time(X, y, timestamps, test_frac=0.2):
    # Time-based split
    order = np.argsort(timestamps.values)
    n = len(order)
    cut = int((1 - test_frac) * n)
    tr_idx, te_idx = order[:cut], order[cut:]
    return (X.iloc[tr_idx], y.iloc[tr_idx]), (X.iloc[te_idx], y.iloc[te_idx])
