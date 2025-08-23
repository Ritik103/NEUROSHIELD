import os
import pandas as pd
import requests
import time
import threading

API_URL = "http://localhost:8000/api/ingest"

# Map router names to their CSV paths
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATA_DIR = os.path.join(BASE_DIR, "datasets")

ROUTER_FILES = {
    "Router_A": os.path.join(DATA_DIR, "Router_A_router_log_15_days.csv"),
    "Router_B": os.path.join(DATA_DIR, "Router_B_router_log_15_days.csv"),
    "Router_C": os.path.join(DATA_DIR, "Router_C_router_log_15_days.csv"),
}

def stream_router(router_name, csv_file, delay=1):
    """Send logs row by row from a router CSV file"""
    df = pd.read_csv(csv_file)

    for _, row in df.iterrows():
        payload = [{
            "Timestamp": row["Timestamp"],
            "Device Name": row["Device Name"],
            "Source IP": row["Source IP"],
            "Destination IP": row["Destination IP"],
            "Traffic Volume (MB/s)": row["Traffic Volume (MB/s)"],
            "Latency (ms)": row["Latency (ms)"],
            "Bandwidth Allocated (MB/s)": row["Bandwidth Allocated (MB/s)"],
            "Bandwidth Used (MB/s)": row["Bandwidth Used (MB/s)"],
            "Congestion Flag": row["Congestion Flag"],
            "Log Text": row["Log Text"],
        }]
        try:
            resp = requests.post(API_URL, json=payload)
            print(f"[{router_name}] Sent {row['Timestamp']} -> {resp.status_code}")
        except Exception as e:
            print(f"[{router_name}] Error: {e}")
        time.sleep(delay)

def main():
    threads = []
    for router, path in ROUTER_FILES.items():
        t = threading.Thread(target=stream_router, args=(router, path))
        threads.append(t)
        t.start()

    # Wait for all threads to finish
    for t in threads:
        t.join()

if __name__ == "__main__":
    print("🚀 Starting multi-router simulation (Router_A, Router_B, Router_C)")
    main()