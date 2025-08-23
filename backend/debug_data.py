#!/usr/bin/env python3
import sqlite3
import pandas as pd
from pathlib import Path

def check_database():
    print("=== DATABASE STATUS ===")
    try:
        conn = sqlite3.connect('metrics.db')
        cursor = conn.cursor()
        
        # Check if table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='router_logs'")
        if cursor.fetchone():
            cursor.execute("SELECT COUNT(*) FROM router_logs")
            count = cursor.fetchone()[0]
            print(f"Database has {count} records")
            
            if count > 0:
                cursor.execute('SELECT DISTINCT "Device Name" FROM router_logs')
                devices = [row[0] for row in cursor.fetchall()]
                print(f"Database devices: {devices}")
        else:
            print("No router_logs table found")
        
        conn.close()
    except Exception as e:
        print(f"Database error: {e}")

def check_csv_files():
    print("\n=== CSV FILES STATUS ===")
    data_dir = Path("../datasets")
    
    csv_files = [
        "Router_A_router_log_15_days.csv",
        "Router_B_router_log_15_days.csv", 
        "Router_C_router_log_15_days.csv"
    ]
    
    for csv_file in csv_files:
        file_path = data_dir / csv_file
        if file_path.exists():
            try:
                df = pd.read_csv(file_path)
                print(f"✓ {csv_file}: {len(df)} records, devices: {df['Device Name'].unique()}")
            except Exception as e:
                print(f"✗ {csv_file}: Error - {e}")
        else:
            print(f"✗ {csv_file}: File not found")

def force_reload_csv():
    print("\n=== FORCING CSV RELOAD ===")
    try:
        # Clear database
        conn = sqlite3.connect('metrics.db')
        conn.execute("DELETE FROM router_logs")
        conn.commit()
        conn.close()
        print("Cleared existing database")
        
        # Force reload from CSV
        from worker.feature_builder import load_router_logs
        df = load_router_logs()
        print(f"Reloaded data: {len(df)} records")
        print(f"Devices found: {df['Device Name'].unique() if not df.empty else 'None'}")
        
    except Exception as e:
        print(f"Reload error: {e}")

if __name__ == "__main__":
    check_database()
    check_csv_files()
    force_reload_csv()
