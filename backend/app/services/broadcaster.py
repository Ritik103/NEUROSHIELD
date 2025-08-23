# backend/app/services/broadcaster.py
import asyncio
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)

class EventType(Enum):
    PREDICTION_UPDATE = "prediction_update"
    SYSTEM_ALERT = "system_alert"
    METRICS_UPDATE = "metrics_update"
    DEVICE_STATUS = "device_status"
    CONGESTION_DETECTED = "congestion_detected"
    ANOMALY_DETECTED = "anomaly_detected"
    ACTION_EXECUTED = "action_executed"

class EventPriority(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

class Event:
    def __init__(self, event_type: EventType, data: Dict[str, Any], 
                 device: Optional[str] = None, priority: EventPriority = EventPriority.MEDIUM):
        self.event_type = event_type
        self.data = data
        self.device = device
        self.priority = priority
        self.timestamp = datetime.now()
        self.id = f"{event_type.value}_{int(self.timestamp.timestamp() * 1000)}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.event_type.value,
            "device": self.device,
            "priority": self.priority.value,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data
        }

class EventBroadcaster:
    def __init__(self):
        self.subscribers = {}  # event_type -> list of callback functions
        self.device_subscribers = {}  # device -> list of callback functions
        self.global_subscribers = []  # callbacks for all events
        self.event_history = []  # keep recent events for replay
        self.max_history = 100
        self.running = False
        self.event_queue = asyncio.Queue()
        
    async def start(self):
        """Start the event processing loop"""
        if not self.running:
            self.running = True
            asyncio.create_task(self._process_events())
            logger.info("Event broadcaster started")

    async def stop(self):
        """Stop the event processing loop"""
        self.running = False
        logger.info("Event broadcaster stopped")

    async def _process_events(self):
        """Main event processing loop"""
        while self.running:
            try:
                # Wait for events with a timeout to allow clean shutdown
                event = await asyncio.wait_for(self.event_queue.get(), timeout=1.0)
                await self._broadcast_event(event)
            except asyncio.TimeoutError:
                continue  # Check if still running
            except Exception as e:
                logger.error(f"Error processing event: {e}")

    async def _broadcast_event(self, event: Event):
        """Broadcast an event to all relevant subscribers"""
        try:
            # Add to history
            self.event_history.append(event)
            if len(self.event_history) > self.max_history:
                self.event_history.pop(0)

            event_dict = event.to_dict()
            
            # Broadcast to global subscribers
            for callback in self.global_subscribers:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(event_dict)
                    else:
                        callback(event_dict)
                except Exception as e:
                    logger.error(f"Error in global subscriber callback: {e}")

            # Broadcast to event type subscribers
            if event.event_type in self.subscribers:
                for callback in self.subscribers[event.event_type]:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(event_dict)
                        else:
                            callback(event_dict)
                    except Exception as e:
                        logger.error(f"Error in event type subscriber callback: {e}")

            # Broadcast to device-specific subscribers
            if event.device and event.device in self.device_subscribers:
                for callback in self.device_subscribers[event.device]:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(event_dict)
                        else:
                            callback(event_dict)
                    except Exception as e:
                        logger.error(f"Error in device subscriber callback: {e}")

            logger.debug(f"Broadcasted event: {event.id}")
            
        except Exception as e:
            logger.error(f"Error broadcasting event: {e}")

    async def emit(self, event_type: EventType, data: Dict[str, Any], 
                   device: Optional[str] = None, priority: EventPriority = EventPriority.MEDIUM):
        """Emit an event"""
        event = Event(event_type, data, device, priority)
        await self.event_queue.put(event)

    def subscribe_to_event_type(self, event_type: EventType, callback):
        """Subscribe to all events of a specific type"""
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(callback)

    def subscribe_to_device(self, device: str, callback):
        """Subscribe to all events for a specific device"""
        if device not in self.device_subscribers:
            self.device_subscribers[device] = []
        self.device_subscribers[device].append(callback)

    def subscribe_to_all(self, callback):
        """Subscribe to all events"""
        self.global_subscribers.append(callback)

    def unsubscribe_from_event_type(self, event_type: EventType, callback):
        """Unsubscribe from events of a specific type"""
        if event_type in self.subscribers:
            try:
                self.subscribers[event_type].remove(callback)
            except ValueError:
                pass

    def unsubscribe_from_device(self, device: str, callback):
        """Unsubscribe from events for a specific device"""
        if device in self.device_subscribers:
            try:
                self.device_subscribers[device].remove(callback)
            except ValueError:
                pass

    def unsubscribe_from_all(self, callback):
        """Unsubscribe from all events"""
        try:
            self.global_subscribers.remove(callback)
        except ValueError:
            pass

    def get_recent_events(self, limit: int = 50, event_type: Optional[EventType] = None, 
                         device: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get recent events, optionally filtered"""
        events = self.event_history[-limit:] if limit > 0 else self.event_history

        if event_type:
            events = [e for e in events if e.event_type == event_type]
        
        if device:
            events = [e for e in events if e.device == device]

        return [e.to_dict() for e in events]

    # Convenience methods for common event types
    async def emit_prediction_update(self, device: str, prediction_data: Dict[str, Any]):
        """Emit a prediction update event"""
        await self.emit(EventType.PREDICTION_UPDATE, prediction_data, device)

    async def emit_system_alert(self, message: str, alert_type: str = "info", 
                               device: Optional[str] = None, priority: EventPriority = EventPriority.MEDIUM):
        """Emit a system alert event"""
        data = {"message": message, "alert_type": alert_type}
        await self.emit(EventType.SYSTEM_ALERT, data, device, priority)

    async def emit_congestion_detected(self, device: str, congestion_prob: float, details: Dict[str, Any]):
        """Emit a congestion detection event"""
        data = {
            "congestion_probability": congestion_prob,
            "details": details
        }
        await self.emit(EventType.CONGESTION_DETECTED, data, device, EventPriority.HIGH)

    async def emit_anomaly_detected(self, device: str, anomaly_score: float, details: Dict[str, Any]):
        """Emit an anomaly detection event"""
        data = {
            "anomaly_score": anomaly_score,
            "details": details
        }
        await self.emit(EventType.ANOMALY_DETECTED, data, device, EventPriority.HIGH)

    async def emit_metrics_update(self, metrics: Dict[str, Any]):
        """Emit a metrics update event"""
        await self.emit(EventType.METRICS_UPDATE, metrics)

    async def emit_action_executed(self, device: str, action: str, result: Dict[str, Any]):
        """Emit an action execution event"""
        data = {
            "action": action,
            "result": result
        }
        await self.emit(EventType.ACTION_EXECUTED, data, device)

# Global broadcaster instance
broadcaster = EventBroadcaster()

# Helper functions to integrate with WebSocket manager
async def setup_websocket_integration():
    """Setup integration between broadcaster and WebSocket manager"""
    try:
        from app.ws import manager as ws_manager
        
        async def websocket_callback(event_data):
            """Forward events to WebSocket clients"""
            message = json.dumps(event_data)
            device = event_data.get("device")
            
            if device:
                await ws_manager.broadcast_to_device_subscribers(device, message)
            else:
                await ws_manager.broadcast(message)
        
        # Subscribe to all events
        broadcaster.subscribe_to_all(websocket_callback)
        logger.info("WebSocket integration setup complete")
        
    except ImportError as e:
        logger.warning(f"WebSocket integration not available: {e}")

async def initialize_broadcaster():
    """Initialize the global broadcaster"""
    await broadcaster.start()
    await setup_websocket_integration()
    logger.info("Event broadcaster initialized")
