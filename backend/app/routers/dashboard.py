# backend/app/routers/dashboard.py
from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import json
import logging
import pandas as pd
import os
import redis.asyncio as redis

from app.services.model_service import ModelService
from app.services.db import db_service
from app.services.network_automation import automation_service, ActionType
from app.services.broadcaster import broadcaster, EventType
from app.ws import websocket_endpoint, manager as ws_manager

logger = logging.getLogger(__name__)

router = APIRouter()
model_service = ModelService()

@router.get("/api/dashboard/overview")
async def get_dashboard_overview():
    """Get overall dashboard overview with key metrics"""
    try:
        # Get all devices
        devices = model_service.get_devices()
        
        # Get recent predictions for all devices
        overview_data = {
            "total_devices": len(devices),
            "devices": [],
            "system_health": "good",
            "active_alerts": 0,
            "total_predictions_today": 0
        }
        
        active_alerts = 0
        
        for device in devices:
            try:
                # Get latest prediction
                prediction = model_service.predict_for_device(device, k=10)
                
                # Get device status from database
                device_status = db_service.get_device_status(device)
                
                device_info = {
                    "name": device,
                    "status": "active" if prediction.get("ok") else "error",
                    "last_prediction": prediction,
                    "congestion_risk": "high" if prediction.get("congestion_prob", 0) > 0.7 else "medium" if prediction.get("congestion_prob", 0) > 0.4 else "low",
                    "anomaly_detected": bool(prediction.get("anomaly", 0)),
                    "last_seen": prediction.get("last_timestamp")
                }
                
                if device_info["congestion_risk"] == "high" or device_info["anomaly_detected"]:
                    active_alerts += 1
                
                overview_data["devices"].append(device_info)
                
            except Exception as e:
                overview_data["devices"].append({
                    "name": device,
                    "status": "error",
                    "error": str(e)
                })
        
        overview_data["active_alerts"] = active_alerts
        if active_alerts > 2:
            overview_data["system_health"] = "warning"
        elif active_alerts > 5:
            overview_data["system_health"] = "critical"
        
        # Get database stats
        db_stats = db_service.get_database_stats()
        overview_data["database_stats"] = db_stats
        
        return overview_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting dashboard overview: {str(e)}")

@router.get("/api/dashboard/automation/policies")
async def get_automation_policies():
    """Get current automation policies"""
    try:
        policies = model_service.get_automation_policies()
        return {
            "policies": policies,
            "last_updated": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting automation policies: {str(e)}")

@router.post("/api/dashboard/automation/policies")
async def update_automation_policies(policies: Dict[str, Any]):
    """Update automation policies"""
    try:
        success = model_service.update_automation_policies(policies)
        if success:
            return {"message": "Policies updated successfully", "policies": model_service.get_automation_policies()}
        else:
            raise HTTPException(status_code=400, detail="Failed to update policies")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating policies: {str(e)}")

@router.get("/api/dashboard/predictions/automated")
async def get_automated_predictions(k: int = Query(120, description="Number of recent data points to use")):
    """Get predictions with automation evaluation for all devices"""
    try:
        predictions = await model_service.evaluate_all_devices_with_automation(k=k)
        return {
            "predictions": predictions,
            "total_devices": len(predictions),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting automated predictions: {str(e)}")

@router.get("/api/dashboard/automation/actions")
async def get_pending_automation_actions():
    """Get pending automation actions from Redis queue"""
    try:
        # Get Redis connection
        r = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"), decode_responses=True)
        action_queue_key = os.getenv("ACTION_QUEUE_KEY", "neuroshield:actions")
        
        # Get all pending actions (sorted by priority)
        actions = await r.zrange(action_queue_key, 0, -1, withscores=True)
        
        parsed_actions = []
        for action_json, score in actions:
            try:
                action_data = json.loads(action_json)
                action_data["priority_score"] = score
                parsed_actions.append(action_data)
            except json.JSONDecodeError:
                continue
        
        # Sort by priority (lower score = higher priority)
        parsed_actions.sort(key=lambda x: x["priority_score"])
        
        return {
            "pending_actions": parsed_actions,
            "total_pending": len(parsed_actions),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting automation actions: {str(e)}")

@router.post("/api/dashboard/automation/actions/{action_id}/execute")
async def execute_automation_action(action_id: str):
    """Execute a specific automation action"""
    try:
        # Get Redis connection
        r = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"), decode_responses=True)
        action_queue_key = os.getenv("ACTION_QUEUE_KEY", "neuroshield:actions")
        
        # Find and remove the action
        actions = await r.zrange(action_queue_key, 0, -1, withscores=True)
        target_action = None
        
        for action_json, score in actions:
            try:
                action_data = json.loads(action_json)
                if action_data.get("timestamp") == action_id:  # Using timestamp as ID
                    target_action = action_data
                    await r.zrem(action_queue_key, action_json)
                    break
            except json.JSONDecodeError:
                continue
        
        if not target_action:
            raise HTTPException(status_code=404, detail="Action not found")
        
        # Execute the action via network automation service
        action_type = target_action["action_type"]
        device = target_action["device"]
        parameters = target_action["parameters"]
        
        # Map action types to automation service
        if action_type == "congestion_mitigation":
            action_id = await automation_service.queue_action(
                ActionType.CONGESTION_MITIGATION,
                device,
                parameters
            )
        elif action_type == "bandwidth_optimization":
            action_id = await automation_service.queue_action(
                ActionType.BANDWIDTH_ADJUSTMENT,
                device,
                parameters
            )
        elif action_type == "latency_optimization":
            action_id = await automation_service.queue_action(
                ActionType.QOS_UPDATE,
                device,
                parameters
            )
        else:
            # Default to general action
            action_id = await automation_service.queue_action(
                ActionType.CONFIG_UPDATE,
                device,
                parameters
            )
        
        return {
            "message": "Action executed successfully",
            "action_id": action_id,
            "action_type": action_type,
            "device": device
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error executing action: {str(e)}")

@router.get("/api/dashboard/device/{device_name}")
async def get_device_dashboard(device_name: str, hours: int = Query(24, description="Hours of data to retrieve")):
    """Get detailed dashboard data for a specific device"""
    try:
        # Get recent predictions
        prediction = model_service.predict_for_device(device_name, k=100)
        
        # Get historical data from database
        cutoff_time = (datetime.now() - timedelta(hours=hours)).isoformat()
        logs_df = db_service.get_router_logs(device_name, limit=1000, start_time=cutoff_time)
        predictions_df = db_service.get_predictions(device_name, limit=100)
        
        # Get device status
        device_status = db_service.get_device_status(device_name)
        
        # Get recent actions for this device
        actions = automation_service.get_all_actions(device_name, limit=20)
        
        # Get recent events
        events = db_service.get_recent_events(limit=50, device_name=device_name)
        
        dashboard_data = {
            "device_name": device_name,
            "current_prediction": prediction,
            "status": device_status[0] if device_status else None,
            "historical_data": {
                "logs_count": len(logs_df) if not logs_df.empty else 0,
                "predictions_count": len(predictions_df) if not predictions_df.empty else 0,
                "recent_logs": logs_df.head(10).to_dict('records') if not logs_df.empty else [],
                "recent_predictions": predictions_df.head(10).to_dict('records') if not predictions_df.empty else []
            },
            "recent_actions": actions,
            "recent_events": events,
            "metrics": _calculate_device_metrics(logs_df) if not logs_df.empty else {}
        }
        
        return dashboard_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting device dashboard: {str(e)}")

@router.get("/api/dashboard/metrics/hourly")
async def get_hourly_metrics(device_name: Optional[str] = None, hours: int = Query(24)):
    """Get hourly aggregated metrics"""
    try:
        metrics_df = db_service.get_hourly_metrics(device_name, hours)
        
        if metrics_df.empty:
            return {"message": "No hourly metrics available", "data": []}
        
        return {
            "data": metrics_df.to_dict('records'),
            "summary": {
                "total_hours": len(metrics_df),
                "devices_covered": metrics_df['device_name'].nunique() if 'device_name' in metrics_df.columns else 1,
                "avg_traffic": metrics_df['avg_traffic_volume'].mean() if 'avg_traffic_volume' in metrics_df.columns else 0,
                "avg_latency": metrics_df['avg_latency'].mean() if 'avg_latency' in metrics_df.columns else 0
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting hourly metrics: {str(e)}")

@router.get("/api/dashboard/alerts")
async def get_active_alerts(device_name: Optional[str] = None, limit: int = Query(50)):
    """Get active alerts and recent events"""
    try:
        # Get recent high-priority events
        events = db_service.get_recent_events(limit, device_name=device_name)
        
        # Filter for alerts and high-priority events
        alerts = []
        for event in events:
            if (event.get('event_type') in ['system_alert', 'congestion_detected', 'anomaly_detected'] or
                event.get('priority', 0) >= 3):
                alerts.append(event)
        
        # Get devices with high congestion probability
        devices = model_service.get_devices()
        congestion_alerts = []
        
        for device in devices:
            try:
                prediction = model_service.predict_for_device(device, k=5)
                if prediction.get("ok") and prediction.get("congestion_prob", 0) > 0.7:
                    congestion_alerts.append({
                        "device": device,
                        "type": "high_congestion_risk",
                        "probability": prediction.get("congestion_prob"),
                        "timestamp": prediction.get("last_timestamp"),
                        "severity": "high"
                    })
                elif prediction.get("anomaly", 0) == 1:
                    congestion_alerts.append({
                        "device": device,
                        "type": "anomaly_detected",
                        "timestamp": prediction.get("last_timestamp"),
                        "severity": "medium"
                    })
            except Exception:
                pass  # Skip device if prediction fails
        
        return {
            "historical_alerts": alerts[:limit//2],
            "current_alerts": congestion_alerts,
            "total_alerts": len(alerts) + len(congestion_alerts)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting alerts: {str(e)}")

@router.get("/api/dashboard/network-topology")
async def get_network_topology():
    """Get network topology information"""
    try:
        devices = model_service.get_devices()
        
        # Get device configurations
        device_configs = automation_service.get_all_device_configs()
        
        topology = {
            "nodes": [],
            "edges": [],
            "summary": {
                "total_devices": len(devices),
                "active_devices": 0,
                "total_bandwidth": 0
            }
        }
        
        for device in devices:
            config = device_configs.get(device, {})
            
            # Get latest status
            try:
                prediction = model_service.predict_for_device(device, k=1)
                status = "active" if prediction.get("ok") else "error"
                if status == "active":
                    topology["summary"]["active_devices"] += 1
            except Exception:
                status = "unknown"
            
            node = {
                "id": device,
                "name": device,
                "type": "router",
                "status": status,
                "management_ip": config.get("management_ip"),
                "max_bandwidth": config.get("max_bandwidth", 100),
                "current_bandwidth": config.get("current_bandwidth", 100),
                "utilization": 0
            }
            
            # Calculate current utilization if possible
            try:
                logs_df = db_service.get_router_logs(device, limit=1)
                if not logs_df.empty:
                    latest_log = logs_df.iloc[0]
                    if 'bandwidth_used' in logs_df.columns and 'bandwidth_allocated' in logs_df.columns:
                        node["utilization"] = (latest_log['bandwidth_used'] / latest_log['bandwidth_allocated']) * 100
            except Exception:
                pass
            
            topology["nodes"].append(node)
            topology["summary"]["total_bandwidth"] += config.get("max_bandwidth", 100)
        
        # Create simple mesh topology (all devices connected to each other)
        for i, device1 in enumerate(devices):
            for j, device2 in enumerate(devices):
                if i < j:  # Avoid duplicate edges
                    topology["edges"].append({
                        "source": device1,
                        "target": device2,
                        "type": "ethernet",
                        "bandwidth": 1000,  # 1Gbps links
                        "status": "active"
                    })
        
        return topology
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting network topology: {str(e)}")

@router.post("/api/dashboard/actions/trigger")
async def trigger_automation_action(action_data: Dict[str, Any]):
    """Trigger an automation action from the dashboard"""
    try:
        action_type_str = action_data.get("action_type")
        device_name = action_data.get("device_name")
        parameters = action_data.get("parameters", {})
        auto_execute = action_data.get("auto_execute", True)
        
        if not action_type_str or not device_name:
            raise HTTPException(status_code=400, detail="action_type and device_name are required")
        
        try:
            action_type = ActionType(action_type_str)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid action type: {action_type_str}")
        
        action_id = await automation_service.queue_action(
            action_type, device_name, parameters, auto_execute=auto_execute
        )
        
        # Emit event
        await broadcaster.emit_system_alert(
            f"Action triggered: {action_type_str} on {device_name}",
            "action_triggered",
            device_name
        )
        
        return {
            "success": True,
            "action_id": action_id,
            "message": f"Action {action_type_str} queued for {device_name}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error triggering action: {str(e)}")

@router.get("/api/dashboard/actions/status/{action_id}")
async def get_action_status(action_id: str):
    """Get status of a specific action"""
    try:
        status = automation_service.get_action_status(action_id)
        if not status:
            raise HTTPException(status_code=404, detail="Action not found")
        
        return status
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting action status: {str(e)}")

@router.get("/api/dashboard/performance")
async def get_performance_metrics():
    """Get system performance metrics"""
    try:
        # Get database statistics
        db_stats = db_service.get_database_stats()
        
        # Get automation service status
        automation_stats = {
            "running_actions": len(automation_service.running_actions),
            "completed_actions": len(automation_service.completed_actions),
            "queue_size": automation_service.action_queue.qsize(),
            "service_running": automation_service.running
        }
        
        # Get WebSocket connections
        ws_stats = {
            "active_connections": len(ws_manager.active_connections),
            "device_subscriptions": len(ws_manager.device_subscriptions)
        }
        
        # Calculate recent prediction accuracy (if available)
        predictions_df = db_service.get_predictions(limit=100)
        prediction_stats = {
            "total_predictions": len(predictions_df) if not predictions_df.empty else 0,
            "recent_predictions": len(predictions_df[predictions_df['created_at'] > (datetime.now() - timedelta(hours=1)).isoformat()]) if not predictions_df.empty else 0
        }
        
        return {
            "database": db_stats,
            "automation": automation_stats,
            "websockets": ws_stats,
            "predictions": prediction_stats,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting performance metrics: {str(e)}")

@router.websocket("/ws/dashboard")
async def dashboard_websocket(websocket: WebSocket):
    """WebSocket endpoint for real-time dashboard updates"""
    await websocket_endpoint(websocket)

def _calculate_device_metrics(logs_df) -> Dict[str, Any]:
    """Calculate metrics from device logs"""
    if logs_df.empty:
        return {}
    
    # Convert columns to numeric if they're not already
    numeric_columns = ['traffic_volume', 'latency', 'bandwidth_used', 'bandwidth_allocated']
    for col in numeric_columns:
        if col in logs_df.columns:
            logs_df[col] = pd.to_numeric(logs_df[col], errors='coerce')
    
    metrics = {}
    
    try:
        if 'traffic_volume' in logs_df.columns:
            metrics['avg_traffic_volume'] = float(logs_df['traffic_volume'].mean())
            metrics['max_traffic_volume'] = float(logs_df['traffic_volume'].max())
        
        if 'latency' in logs_df.columns:
            metrics['avg_latency'] = float(logs_df['latency'].mean())
            metrics['max_latency'] = float(logs_df['latency'].max())
        
        if 'bandwidth_used' in logs_df.columns and 'bandwidth_allocated' in logs_df.columns:
            utilization = (logs_df['bandwidth_used'] / logs_df['bandwidth_allocated']) * 100
            metrics['avg_utilization'] = float(utilization.mean())
            metrics['max_utilization'] = float(utilization.max())
        
        # Count congestion events
        if 'congestion_flag' in logs_df.columns:
            congestion_count = len(logs_df[logs_df['congestion_flag'].str.upper() == 'YES'])
            metrics['congestion_events'] = int(congestion_count)
            metrics['congestion_rate'] = float(congestion_count / len(logs_df)) if len(logs_df) > 0 else 0
        
        metrics['total_records'] = len(logs_df)
        
    except Exception as e:
        logger.warning(f"Error calculating metrics: {e}")
    
    return metrics
