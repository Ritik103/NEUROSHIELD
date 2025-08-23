import os
import pandas as pd
import requests
import time

# Choose which router log to replay
CSV_FILE = os.path.join("..", "datasets", "Router_A_router_log_15_days.csv")
CSV_FILE = os.path.join("..", "datasets", "Router_B_router_log_15_days.csv")
CSV_FILE = os.path.join("..", "datasets", "Router_C_router_log_15_days.csv")
API_URL = "http://localhost:8000/api/ingest"

# Load CSV
df = pd.read_csv(CSV_FILE)

# Iterate through rows and send to FastAPI
for _, row in df.iterrows():
    payload = [  # must send as list
        {
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
        }
    ]
    
    try:
        resp = requests.post(API_URL, json=payload)
        print(f"Sent row at {row['Timestamp']} -> Status {resp.status_code}")
    except Exception as e:
        print("Error sending row:", e)
    
    time.sleep(1)  # simulate 1 second per log row