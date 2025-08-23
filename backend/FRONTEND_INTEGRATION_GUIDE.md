# NEUROSHIELD Backend - Frontend Integration Guide

## 🚨 **Current Backend Status**

### **Backend Status: ⚠️ PARTIALLY WORKING**
- ✅ **Core Logic**: All prediction and automation logic is working
- ✅ **Database**: SQLite database is functional and consistent
- ✅ **Models**: ML models are loaded and predictions work
- ❌ **FastAPI Server**: Server startup issues (needs debugging)
- ❌ **Redis**: Not running (required for action queue)

### **What's Working:**
- All prediction algorithms
- Database operations
- Model service
- Automation policies
- Data processing

### **What Needs Fixing:**
- FastAPI server startup
- Redis connection for action queue

---

## 📊 **Data Formats for Frontend Integration**

### **1. Prediction Data Format**

#### **Single Device Prediction Response:**
```json
{
  "device": "Router_A",
  "ok": true,
  "last_timestamp": "2025-08-23 19:12:13",
  "congestion_prob": 0.171,
  "congestion_pred": 0,
  "anomaly": 0,
  "threshold": 0.6,
  "model": "logreg"
}
```

#### **All Devices Prediction Response:**
```json
{
  "devices": [
    {
      "device": "Router_A",
      "ok": true,
      "last_timestamp": "2025-08-23 19:12:13",
      "congestion_prob": 0.171,
      "congestion_pred": 0,
      "anomaly": 0,
      "threshold": 0.6,
      "model": "logreg"
    },
    {
      "device": "Router_B",
      "ok": true,
      "last_timestamp": "2025-08-23 19:12:13",
      "congestion_prob": 0.244,
      "congestion_pred": 0,
      "anomaly": 0,
      "threshold": 0.6,
      "model": "logreg"
    },
    {
      "device": "Router_C",
      "ok": true,
      "last_timestamp": "2025-08-23 19:12:13",
      "congestion_prob": 0.258,
      "congestion_pred": 0,
      "anomaly": 0,
      "threshold": 0.6,
      "model": "logreg"
    }
  ]
}
```

### **2. Dashboard Overview Data Format**

```json
{
  "total_devices": 3,
  "devices": [
    {
      "name": "Router_A",
      "status": "active",
      "last_prediction": {
        "device": "Router_A",
        "ok": true,
        "congestion_prob": 0.171,
        "congestion_pred": 0,
        "anomaly": 0,
        "last_timestamp": "2025-08-23 19:12:13"
      },
      "congestion_risk": "low",
      "anomaly_detected": false,
      "last_seen": "2025-08-23 19:12:13"
    }
  ],
  "system_health": "good",
  "active_alerts": 0,
  "total_predictions_today": 0,
  "database_stats": {
    "router_logs_count": 1086,
    "predictions_count": 0,
    "actions_log_count": 0,
    "events_count": 0,
    "device_status_count": 0,
    "metrics_hourly_count": 0,
    "db_size_mb": 0.23
  }
}
```

### **3. Automation Policies Data Format**

```json
{
  "policies": {
    "congestion_threshold": 0.6,
    "anomaly_threshold": 0.8,
    "high_utilization_threshold": 0.85,
    "latency_threshold": 50.0
  },
  "last_updated": "2025-08-24T01:00:00.000000"
}
```

### **4. Device Dashboard Data Format**

```json
{
  "device_name": "Router_A",
  "current_prediction": {
    "device": "Router_A",
    "ok": true,
    "congestion_prob": 0.171,
    "congestion_pred": 0,
    "anomaly": 0,
    "last_timestamp": "2025-08-23 19:12:13"
  },
  "status": {
    "device_name": "Router_A",
    "last_seen": "2025-08-24T01:00:00.000000",
    "status": "active",
    "alerts_count": 0
  },
  "historical_data": {
    "logs_count": 362,
    "predictions_count": 0,
    "recent_logs": [
      {
        "id": 1086,
        "timestamp": "2025-08-23 19:12:13",
        "device_name": "Router_A",
        "source_ip": "192.168.1.100",
        "destination_ip": "10.0.0.50",
        "traffic_volume": 45.2,
        "latency": 12.5,
        "bandwidth_allocated": 100.0,
        "bandwidth_used": 45.2,
        "congestion_flag": "No",
        "log_text": "Normal traffic flow"
      }
    ],
    "recent_predictions": []
  },
  "recent_actions": [],
  "recent_events": [],
  "metrics": {
    "avg_traffic_volume": 42.3,
    "max_traffic_volume": 89.7,
    "avg_latency": 15.2,
    "max_latency": 45.8,
    "avg_utilization": 42.3,
    "max_utilization": 89.7,
    "congestion_events": 0,
    "congestion_rate": 0.0,
    "total_records": 362
  }
}
```

### **5. WebSocket Message Formats**

#### **Prediction Update Message:**
```json
{
  "type": "prediction_update",
  "device": "Router_A",
  "timestamp": "2025-08-24T01:00:00.000000",
  "data": {
    "device": "Router_A",
    "ok": true,
    "congestion_prob": 0.171,
    "congestion_pred": 0,
    "anomaly": 0,
    "last_timestamp": "2025-08-23 19:12:13"
  }
}
```

#### **Automation Update Message:**
```json
{
  "type": "automation_update",
  "device": "Router_A",
  "timestamp": "2025-08-24T01:00:00.000000",
  "data": {
    "action_type": "congestion_mitigation",
    "parameters": {
      "congestion_probability": 0.75,
      "severity": "high"
    },
    "priority": 2,
    "status": "queued"
  }
}
```

#### **System Alert Message:**
```json
{
  "type": "system_alert",
  "alert_type": "high_congestion",
  "message": "High congestion detected on Router_A",
  "device": "Router_A",
  "timestamp": "2025-08-24T01:00:00.000000"
}
```

#### **Policy Update Message:**
```json
{
  "type": "policy_update",
  "timestamp": "2025-08-24T01:00:00.000000",
  "data": {
    "congestion_threshold": 0.7,
    "anomaly_threshold": 0.9
  }
}
```

---

## 🔌 **API Endpoints for Frontend**

### **Prediction Endpoints:**
- `GET /api/predict/all` - Get predictions for all devices
- `GET /api/predict/device/{device}` - Get prediction for specific device
- `GET /api/predict/automated` - Get predictions with automation evaluation
- `GET /api/predict/device/{device}/automated` - Get automated prediction for device

### **Dashboard Endpoints:**
- `GET /api/dashboard/overview` - Get dashboard overview
- `GET /api/dashboard/device/{device_name}` - Get device-specific dashboard
- `GET /api/dashboard/automation/policies` - Get current automation policies
- `POST /api/dashboard/automation/policies` - Update automation policies
- `GET /api/dashboard/automation/actions` - Get pending automation actions
- `GET /api/dashboard/alerts` - Get active alerts
- `GET /api/dashboard/performance` - Get system performance metrics
- `GET /api/dashboard/network-topology` - Get network topology

### **Action Endpoints:**
- `POST /api/dashboard/actions/trigger` - Trigger automation action
- `GET /api/dashboard/actions/status/{action_id}` - Get action status

### **Data Ingestion:**
- `POST /api/ingest` - Ingest router logs

### **WebSocket Endpoints:**
- `ws://localhost:8000/ws` - Main WebSocket endpoint
- `ws://localhost:8000/ws/dashboard` - Dashboard-specific WebSocket

---

## 📡 **WebSocket Integration Guide**

### **Connecting to WebSocket:**
```javascript
const ws = new WebSocket('ws://localhost:8000/ws');

ws.onopen = function() {
    console.log('Connected to NEUROSHIELD WebSocket');
    
    // Subscribe to device updates
    ws.send(JSON.stringify({
        type: 'subscribe',
        device: 'Router_A'
    }));
};

ws.onmessage = function(event) {
    const message = JSON.parse(event.data);
    
    switch(message.type) {
        case 'prediction_update':
            handlePredictionUpdate(message);
            break;
        case 'automation_update':
            handleAutomationUpdate(message);
            break;
        case 'system_alert':
            handleSystemAlert(message);
            break;
        case 'policy_update':
            handlePolicyUpdate(message);
            break;
    }
};
```

### **WebSocket Message Types:**
1. **prediction_update** - Real-time prediction updates
2. **automation_update** - Automation action notifications
3. **system_alert** - System alerts and warnings
4. **policy_update** - Policy changes
5. **metrics_update** - General metrics updates

---

## 🎨 **Frontend Data Visualization Recommendations**

### **1. Dashboard Components:**

#### **Device Status Cards:**
```javascript
// Display device status with congestion probability
const deviceCard = {
    name: "Router_A",
    status: "active", // active, error, warning
    congestionProb: 0.171,
    riskLevel: "low", // low, medium, high
    lastSeen: "2025-08-23 19:12:13",
    anomaly: false
};
```

#### **Real-time Charts:**
```javascript
// Time series data for charts
const chartData = {
    labels: ["19:10", "19:11", "19:12", "19:13"],
    datasets: [{
        label: 'Congestion Probability',
        data: [0.15, 0.17, 0.18, 0.17],
        borderColor: '#ff6384'
    }]
};
```

#### **Alert System:**
```javascript
// Alert data structure
const alert = {
    type: "high_congestion",
    severity: "high", // low, medium, high
    device: "Router_A",
    message: "High congestion detected",
    timestamp: "2025-08-24T01:00:00.000000",
    acknowledged: false
};
```

### **2. Color Coding:**
- **Green**: Normal operation (congestion_prob < 0.4)
- **Yellow**: Warning (congestion_prob 0.4 - 0.6)
- **Orange**: High risk (congestion_prob 0.6 - 0.8)
- **Red**: Critical (congestion_prob > 0.8)

---

## 🚀 **Getting Started with Frontend Integration**

### **1. Test Backend First:**
```bash
# Run the comprehensive test
python test_complete_functionality.py

# Test predictions
python test_predictions.py

# Test automation policies
python test_automation_policy.py
```

### **2. Start Backend Server (when fixed):**
```bash
python start_server.py
```

### **3. Test API Endpoints:**
```bash
# Test all endpoints
python test_api_endpoints.py
```

### **4. Frontend Integration Steps:**
1. **Connect to WebSocket** for real-time updates
2. **Fetch initial data** from dashboard endpoints
3. **Implement polling** for regular updates (fallback)
4. **Handle WebSocket messages** for real-time updates
5. **Display data** using the provided formats

---

## ⚠️ **Current Issues to Fix**

### **1. FastAPI Server Startup:**
- Server not starting properly
- Need to debug startup issues
- Check for missing dependencies

### **2. Redis Connection:**
- Redis not running
- Required for action queue functionality
- Can work without Redis for basic functionality

### **3. Service Initialization:**
- Some services may not be initializing properly
- Need to check service startup sequence

---

## ✅ **What's Ready for Frontend**

### **✅ Ready Components:**
- All data formats and structures
- API endpoint specifications
- WebSocket message formats
- Prediction algorithms
- Database operations
- Automation policies

### **✅ Working Features:**
- Device predictions (Router_A, Router_B, Router_C)
- Congestion probability calculations
- Anomaly detection
- Policy-based automation
- Database storage and retrieval

### **⚠️ Needs Fixing:**
- FastAPI server startup
- Redis connection
- Service initialization

---

## 📋 **Frontend Development Checklist**

- [ ] **Backend Testing**: Run all test scripts
- [ ] **API Integration**: Implement API calls to all endpoints
- [ ] **WebSocket Integration**: Connect to WebSocket endpoints
- [ ] **Real-time Updates**: Handle WebSocket messages
- [ ] **Data Visualization**: Create charts and dashboards
- [ ] **Alert System**: Implement alert handling
- [ ] **Error Handling**: Handle API errors and connection issues
- [ ] **Responsive Design**: Make dashboard responsive
- [ ] **Testing**: Test with real data

---

*This guide provides all the data formats and integration details needed for frontend development. The backend logic is working, but the server startup needs to be fixed.*
