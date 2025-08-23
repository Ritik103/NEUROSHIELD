# backend/app/ws.py
from fastapi import WebSocket, WebSocketDisconnect
from typing import List
import json
import asyncio
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.device_subscriptions = {}  # websocket -> set of device names

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        if websocket in self.device_subscriptions:
            del self.device_subscriptions[websocket]
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")

    async def send_personal_message(self, message: str, websocket: WebSocket):
        try:
            await websocket.send_text(message)
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
            self.disconnect(websocket)

    async def broadcast(self, message: str):
        """Broadcast to all connected clients"""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Error broadcasting to connection: {e}")
                disconnected.append(connection)
        
        # Clean up disconnected clients
        for conn in disconnected:
            self.disconnect(conn)

    async def broadcast_to_device_subscribers(self, device: str, message: str):
        """Broadcast only to clients subscribed to a specific device"""
        disconnected = []
        for connection, devices in self.device_subscriptions.items():
            if device in devices:
                try:
                    await connection.send_text(message)
                except Exception as e:
                    logger.error(f"Error broadcasting to device subscriber: {e}")
                    disconnected.append(connection)
        
        # Clean up disconnected clients
        for conn in disconnected:
            self.disconnect(conn)

    def subscribe_to_device(self, websocket: WebSocket, device: str):
        """Subscribe a websocket to updates for a specific device"""
        if websocket not in self.device_subscriptions:
            self.device_subscriptions[websocket] = set()
        self.device_subscriptions[websocket].add(device)

    def unsubscribe_from_device(self, websocket: WebSocket, device: str):
        """Unsubscribe a websocket from updates for a specific device"""
        if websocket in self.device_subscriptions:
            self.device_subscriptions[websocket].discard(device)

    async def send_prediction_update(self, device: str, prediction_data: dict):
        """Send real-time prediction updates for a device"""
        message = {
            "type": "prediction_update",
            "device": device,
            "timestamp": datetime.now().isoformat(),
            "data": prediction_data
        }
        await self.broadcast_to_device_subscribers(device, json.dumps(message))

    async def send_automation_update(self, device: str, action_data: dict):
        """Send real-time automation action updates for a device"""
        message = {
            "type": "automation_update",
            "device": device,
            "timestamp": datetime.now().isoformat(),
            "data": action_data
        }
        await self.broadcast_to_device_subscribers(device, json.dumps(message))

    async def send_policy_update(self, policy_data: dict):
        """Send policy updates to all subscribers"""
        message = {
            "type": "policy_update",
            "timestamp": datetime.now().isoformat(),
            "data": policy_data
        }
        await self.broadcast(json.dumps(message))

    async def send_system_alert(self, alert_type: str, message: str, device: str = None):
        """Send system alerts"""
        alert = {
            "type": "system_alert",
            "alert_type": alert_type,
            "message": message,
            "device": device,
            "timestamp": datetime.now().isoformat()
        }
        
        if device:
            await self.broadcast_to_device_subscribers(device, json.dumps(alert))
        else:
            await self.broadcast(json.dumps(alert))

    async def send_metrics_update(self, metrics: dict):
        """Send general metrics updates"""
        message = {
            "type": "metrics_update",
            "timestamp": datetime.now().isoformat(),
            "data": metrics
        }
        await self.broadcast(json.dumps(message))

# Global connection manager instance
manager = ConnectionManager()

async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                await handle_websocket_message(websocket, message)
            except json.JSONDecodeError:
                await manager.send_personal_message(
                    json.dumps({"error": "Invalid JSON format"}), 
                    websocket
                )
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)

async def handle_websocket_message(websocket: WebSocket, message: dict):
    """Handle incoming WebSocket messages from clients"""
    msg_type = message.get("type")
    
    if msg_type == "subscribe":
        device = message.get("device")
        if device:
            manager.subscribe_to_device(websocket, device)
            await manager.send_personal_message(
                json.dumps({
                    "type": "subscription_confirmed",
                    "device": device,
                    "message": f"Subscribed to {device} updates"
                }),
                websocket
            )
    
    elif msg_type == "unsubscribe":
        device = message.get("device")
        if device:
            manager.unsubscribe_from_device(websocket, device)
            await manager.send_personal_message(
                json.dumps({
                    "type": "unsubscription_confirmed", 
                    "device": device,
                    "message": f"Unsubscribed from {device} updates"
                }),
                websocket
            )
    
    elif msg_type == "ping":
        await manager.send_personal_message(
            json.dumps({
                "type": "pong",
                "timestamp": datetime.now().isoformat()
            }),
            websocket
        )
    
    else:
        await manager.send_personal_message(
            json.dumps({"error": f"Unknown message type: {msg_type}"}),
            websocket
        )
