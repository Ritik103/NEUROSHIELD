import requests

sample_payload = [{
    "Timestamp": "2024-04-20 00:00:00",
    "Device Name": "Router_A",
    "Source IP": "192.168.1.1",
    "Destination IP": "192.168.2.1",
    "Traffic Volume (MB/s)": 50.5,
    "Latency (ms)": 20.1,
    "Bandwidth Allocated (MB/s)": 100,
    "Bandwidth Used (MB/s)": 80,
    "Congestion Flag": "No",
    "Log Text": "Normal operation"
}]

resp = requests.post("http://localhost:8000/api/ingest", json=sample_payload)

print("Status:", resp.status_code)
print("Response:", resp.json())