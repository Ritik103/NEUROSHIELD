# backend/app/services/network_automation.py
import asyncio
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from enum import Enum
import time

logger = logging.getLogger(__name__)

class ActionType(Enum):
    BANDWIDTH_ADJUSTMENT = "bandwidth_adjustment"
    TRAFFIC_REROUTING = "traffic_rerouting"
    QOS_UPDATE = "qos_update"
    CONGESTION_MITIGATION = "congestion_mitigation"
    ALERT_NOTIFICATION = "alert_notification"
    DEVICE_RESTART = "device_restart"
    CONFIG_UPDATE = "config_update"
    MONITORING_ENABLE = "monitoring_enable"

class ActionStatus(Enum):
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class NetworkAction:
    def __init__(self, action_type: ActionType, device_name: str, parameters: Dict[str, Any], 
                 priority: int = 1, auto_execute: bool = True):
        self.action_type = action_type
        self.device_name = device_name
        self.parameters = parameters
        self.priority = priority
        self.auto_execute = auto_execute
        self.status = ActionStatus.QUEUED
        self.created_at = datetime.now()
        self.started_at = None
        self.completed_at = None
        self.result = {}
        self.error_message = None
        self.id = f"{action_type.value}_{device_name}_{int(time.time() * 1000)}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "action_type": self.action_type.value,
            "device_name": self.device_name,
            "parameters": self.parameters,
            "priority": self.priority,
            "auto_execute": self.auto_execute,
            "status": self.status.value,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "result": self.result,
            "error_message": self.error_message
        }

class NetworkAutomationService:
    def __init__(self):
        self.action_queue = asyncio.Queue()
        self.running_actions = {}  # action_id -> NetworkAction
        self.completed_actions = []  # Keep history
        self.max_history = 100
        self.running = False
        self.max_concurrent_actions = 3
        
        # Device configurations (simulated)
        self.device_configs = {
            "Router_A": {
                "management_ip": "192.168.100.1",
                "max_bandwidth": 100,
                "current_bandwidth": 100,
                "qos_policies": ["high", "medium", "low"],
                "routing_table": [],
                "status": "active"
            },
            "Router_B": {
                "management_ip": "192.168.100.2",
                "max_bandwidth": 100,
                "current_bandwidth": 100,
                "qos_policies": ["high", "medium", "low"],
                "routing_table": [],
                "status": "active"
            },
            "Router_C": {
                "management_ip": "192.168.100.3",
                "max_bandwidth": 100,
                "current_bandwidth": 100,
                "qos_policies": ["high", "medium", "low"],
                "routing_table": [],
                "status": "active"
            }
        }

    async def start(self):
        """Start the automation service"""
        if not self.running:
            self.running = True
            asyncio.create_task(self._process_actions())
            logger.info("Network automation service started")

    async def stop(self):
        """Stop the automation service"""
        self.running = False
        logger.info("Network automation service stopped")

    async def _process_actions(self):
        """Main action processing loop"""
        while self.running:
            try:
                # Process actions from queue
                if len(self.running_actions) < self.max_concurrent_actions:
                    try:
                        action = await asyncio.wait_for(self.action_queue.get(), timeout=1.0)
                        if action.auto_execute:
                            asyncio.create_task(self._execute_action(action))
                        else:
                            # Add to pending actions waiting for manual approval
                            self.running_actions[action.id] = action
                            await self._notify_action_pending(action)
                    except asyncio.TimeoutError:
                        continue
                
                await asyncio.sleep(0.1)  # Small delay to prevent CPU spinning
                
            except Exception as e:
                logger.error(f"Error in action processing loop: {e}")

    async def _execute_action(self, action: NetworkAction):
        """Execute a network action"""
        action.status = ActionStatus.IN_PROGRESS
        action.started_at = datetime.now()
        self.running_actions[action.id] = action
        
        try:
            await self._notify_action_started(action)
            
            # Route to specific action handler
            if action.action_type == ActionType.BANDWIDTH_ADJUSTMENT:
                result = await self._execute_bandwidth_adjustment(action)
            elif action.action_type == ActionType.TRAFFIC_REROUTING:
                result = await self._execute_traffic_rerouting(action)
            elif action.action_type == ActionType.QOS_UPDATE:
                result = await self._execute_qos_update(action)
            elif action.action_type == ActionType.CONGESTION_MITIGATION:
                result = await self._execute_congestion_mitigation(action)
            elif action.action_type == ActionType.ALERT_NOTIFICATION:
                result = await self._execute_alert_notification(action)
            elif action.action_type == ActionType.DEVICE_RESTART:
                result = await self._execute_device_restart(action)
            elif action.action_type == ActionType.CONFIG_UPDATE:
                result = await self._execute_config_update(action)
            elif action.action_type == ActionType.MONITORING_ENABLE:
                result = await self._execute_monitoring_enable(action)
            else:
                raise ValueError(f"Unknown action type: {action.action_type}")
            
            action.result = result
            action.status = ActionStatus.COMPLETED
            action.completed_at = datetime.now()
            
            await self._notify_action_completed(action)
            logger.info(f"Action completed: {action.id}")
            
        except Exception as e:
            action.status = ActionStatus.FAILED
            action.error_message = str(e)
            action.completed_at = datetime.now()
            
            await self._notify_action_failed(action)
            logger.error(f"Action failed: {action.id} - {e}")
        
        finally:
            # Move to completed actions
            if action.id in self.running_actions:
                del self.running_actions[action.id]
            
            self.completed_actions.append(action)
            if len(self.completed_actions) > self.max_history:
                self.completed_actions.pop(0)

    async def _execute_bandwidth_adjustment(self, action: NetworkAction) -> Dict[str, Any]:
        """Execute bandwidth adjustment"""
        device_name = action.device_name
        new_bandwidth = action.parameters.get("bandwidth", 100)
        
        # Simulate bandwidth adjustment
        await asyncio.sleep(2)  # Simulate network call delay
        
        if device_name in self.device_configs:
            old_bandwidth = self.device_configs[device_name]["current_bandwidth"]
            self.device_configs[device_name]["current_bandwidth"] = new_bandwidth
            
            return {
                "success": True,
                "old_bandwidth": old_bandwidth,
                "new_bandwidth": new_bandwidth,
                "message": f"Bandwidth adjusted from {old_bandwidth} to {new_bandwidth} MB/s"
            }
        else:
            raise ValueError(f"Device {device_name} not found")

    async def _execute_traffic_rerouting(self, action: NetworkAction) -> Dict[str, Any]:
        """Execute traffic rerouting"""
        await asyncio.sleep(3)  # Simulate network configuration time
        
        source_route = action.parameters.get("source_route")
        target_route = action.parameters.get("target_route")
        
        return {
            "success": True,
            "source_route": source_route,
            "target_route": target_route,
            "message": f"Traffic rerouted from {source_route} to {target_route}"
        }

    async def _execute_qos_update(self, action: NetworkAction) -> Dict[str, Any]:
        """Execute QoS policy update"""
        await asyncio.sleep(1.5)
        
        policy = action.parameters.get("policy", "medium")
        priority_flows = action.parameters.get("priority_flows", [])
        
        return {
            "success": True,
            "policy": policy,
            "priority_flows": priority_flows,
            "message": f"QoS policy updated to {policy}"
        }

    async def _execute_congestion_mitigation(self, action: NetworkAction) -> Dict[str, Any]:
        """Execute congestion mitigation actions"""
        await asyncio.sleep(2.5)
        
        mitigation_type = action.parameters.get("type", "bandwidth_limit")
        severity = action.parameters.get("severity", "medium")
        
        actions_taken = []
        
        if mitigation_type == "bandwidth_limit":
            # Reduce bandwidth allocation temporarily
            actions_taken.append("Reduced bandwidth allocation by 20%")
        elif mitigation_type == "traffic_shaping":
            # Apply traffic shaping
            actions_taken.append("Applied aggressive traffic shaping")
        elif mitigation_type == "load_balancing":
            # Redistribute load
            actions_taken.append("Redistributed traffic load across alternate paths")
        
        return {
            "success": True,
            "mitigation_type": mitigation_type,
            "severity": severity,
            "actions_taken": actions_taken,
            "message": f"Congestion mitigation applied: {mitigation_type}"
        }

    async def _execute_alert_notification(self, action: NetworkAction) -> Dict[str, Any]:
        """Execute alert notification"""
        await asyncio.sleep(0.5)
        
        recipients = action.parameters.get("recipients", ["admin@company.com"])
        alert_type = action.parameters.get("alert_type", "info")
        message = action.parameters.get("message", "Network alert")
        
        # Simulate sending notifications
        return {
            "success": True,
            "recipients": recipients,
            "alert_type": alert_type,
            "message": f"Alert sent to {len(recipients)} recipients"
        }

    async def _execute_device_restart(self, action: NetworkAction) -> Dict[str, Any]:
        """Execute device restart (simulated)"""
        await asyncio.sleep(10)  # Simulate restart time
        
        device_name = action.device_name
        restart_type = action.parameters.get("type", "soft")
        
        if device_name in self.device_configs:
            # Simulate device restart
            self.device_configs[device_name]["status"] = "restarting"
            await asyncio.sleep(5)
            self.device_configs[device_name]["status"] = "active"
            
            return {
                "success": True,
                "restart_type": restart_type,
                "downtime_seconds": 15,
                "message": f"Device {device_name} restarted successfully"
            }
        else:
            raise ValueError(f"Device {device_name} not found")

    async def _execute_config_update(self, action: NetworkAction) -> Dict[str, Any]:
        """Execute configuration update"""
        await asyncio.sleep(3)
        
        config_section = action.parameters.get("section", "general")
        config_data = action.parameters.get("config", {})
        
        return {
            "success": True,
            "section": config_section,
            "updated_keys": list(config_data.keys()),
            "message": f"Configuration updated for section: {config_section}"
        }

    async def _execute_monitoring_enable(self, action: NetworkAction) -> Dict[str, Any]:
        """Execute monitoring configuration"""
        await asyncio.sleep(1)
        
        monitoring_type = action.parameters.get("type", "enhanced")
        interval = action.parameters.get("interval", 60)
        
        return {
            "success": True,
            "monitoring_type": monitoring_type,
            "interval": interval,
            "message": f"Enhanced monitoring enabled with {interval}s interval"
        }

    # Notification methods (integrate with broadcaster)
    async def _notify_action_pending(self, action: NetworkAction):
        """Notify that an action is pending approval"""
        try:
            from app.services.broadcaster import broadcaster
            await broadcaster.emit_system_alert(
                f"Action pending approval: {action.action_type.value}",
                "pending_action",
                action.device_name
            )
        except ImportError:
            logger.warning("Broadcaster not available for notifications")

    async def _notify_action_started(self, action: NetworkAction):
        """Notify that an action has started"""
        try:
            from app.services.broadcaster import broadcaster
            await broadcaster.emit_action_executed(
                action.device_name,
                action.action_type.value,
                {"status": "started", "parameters": action.parameters}
            )
        except ImportError:
            logger.warning("Broadcaster not available for notifications")

    async def _notify_action_completed(self, action: NetworkAction):
        """Notify that an action has completed"""
        try:
            from app.services.broadcaster import broadcaster
            await broadcaster.emit_action_executed(
                action.device_name,
                action.action_type.value,
                {"status": "completed", "result": action.result}
            )
        except ImportError:
            logger.warning("Broadcaster not available for notifications")

    async def _notify_action_failed(self, action: NetworkAction):
        """Notify that an action has failed"""
        try:
            from app.services.broadcaster import broadcaster
            await broadcaster.emit_system_alert(
                f"Action failed: {action.error_message}",
                "error",
                action.device_name
            )
        except ImportError:
            logger.warning("Broadcaster not available for notifications")

    # Public methods
    async def queue_action(self, action_type: ActionType, device_name: str, 
                          parameters: Dict[str, Any], priority: int = 1, 
                          auto_execute: bool = True) -> str:
        """Queue a network action"""
        action = NetworkAction(action_type, device_name, parameters, priority, auto_execute)
        await self.action_queue.put(action)
        
        # Store in database
        try:
            from app.services.db import db_service
            db_service.insert_action(device_name, action_type.value, parameters)
        except ImportError:
            logger.warning("Database service not available")
        
        logger.info(f"Action queued: {action.id}")
        return action.id

    async def cancel_action(self, action_id: str) -> bool:
        """Cancel a queued or running action"""
        if action_id in self.running_actions:
            action = self.running_actions[action_id]
            if action.status in [ActionStatus.QUEUED, ActionStatus.IN_PROGRESS]:
                action.status = ActionStatus.CANCELLED
                action.completed_at = datetime.now()
                action.error_message = "Action cancelled by user"
                return True
        return False

    def get_action_status(self, action_id: str) -> Optional[Dict[str, Any]]:
        """Get status of an action"""
        # Check running actions
        if action_id in self.running_actions:
            return self.running_actions[action_id].to_dict()
        
        # Check completed actions
        for action in self.completed_actions:
            if action.id == action_id:
                return action.to_dict()
        
        return None

    def get_all_actions(self, device_name: str = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Get all actions (running and completed)"""
        all_actions = list(self.running_actions.values()) + self.completed_actions
        
        if device_name:
            all_actions = [a for a in all_actions if a.device_name == device_name]
        
        # Sort by creation time (newest first)
        all_actions.sort(key=lambda x: x.created_at, reverse=True)
        
        return [action.to_dict() for action in all_actions[:limit]]

    def get_device_config(self, device_name: str) -> Optional[Dict[str, Any]]:
        """Get current device configuration"""
        return self.device_configs.get(device_name)

    def get_all_device_configs(self) -> Dict[str, Any]:
        """Get all device configurations"""
        return self.device_configs.copy()

    # Convenience methods for common actions
    async def adjust_bandwidth(self, device_name: str, bandwidth: float, auto_execute: bool = True) -> str:
        """Convenience method to adjust bandwidth"""
        return await self.queue_action(
            ActionType.BANDWIDTH_ADJUSTMENT,
            device_name,
            {"bandwidth": bandwidth},
            auto_execute=auto_execute
        )

    async def mitigate_congestion(self, device_name: str, severity: str = "medium", auto_execute: bool = True) -> str:
        """Convenience method to mitigate congestion"""
        return await self.queue_action(
            ActionType.CONGESTION_MITIGATION,
            device_name,
            {"type": "bandwidth_limit", "severity": severity},
            priority=2,
            auto_execute=auto_execute
        )

    async def send_alert(self, device_name: str, message: str, alert_type: str = "warning") -> str:
        """Convenience method to send alerts"""
        return await self.queue_action(
            ActionType.ALERT_NOTIFICATION,
            device_name,
            {"message": message, "alert_type": alert_type, "recipients": ["admin@company.com"]}
        )

# Global automation service instance
automation_service = NetworkAutomationService()

async def initialize_automation_service():
    """Initialize the global automation service"""
    await automation_service.start()
    logger.info("Network automation service initialized")
