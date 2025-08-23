#!/usr/bin/env python3
"""
Redis Action Processor Service
Processes automation actions from Redis queue and executes them
"""

import asyncio
import json
import logging
import os
from typing import Dict, Any, Optional
from datetime import datetime
import redis.asyncio as redis

from app.services.network_automation import automation_service, ActionType
from app.services.broadcaster import broadcaster
from app.ws import manager as ws_manager

logger = logging.getLogger(__name__)

class RedisActionProcessor:
    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.action_queue_key = os.getenv("ACTION_QUEUE_KEY", "neuroshield:actions")
        self.running = False
        self.processing_interval = 5  # seconds
        
    async def _get_redis_connection(self):
        """Get Redis connection"""
        try:
            return redis.from_url(self.redis_url, decode_responses=True)
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            return None
    
    async def start(self):
        """Start the action processor"""
        if not self.running:
            self.running = True
            logger.info("Redis action processor started")
            asyncio.create_task(self._process_actions_loop())
    
    async def stop(self):
        """Stop the action processor"""
        self.running = False
        logger.info("Redis action processor stopped")
    
    async def _process_actions_loop(self):
        """Main loop for processing actions"""
        while self.running:
            try:
                await self._process_pending_actions()
                await asyncio.sleep(self.processing_interval)
            except Exception as e:
                logger.error(f"Error in action processing loop: {e}")
                await asyncio.sleep(self.processing_interval)
    
    async def _process_pending_actions(self):
        """Process all pending actions from Redis queue"""
        try:
            r = await self._get_redis_connection()
            if not r:
                return
            
            # Get all pending actions (sorted by priority)
            actions = await r.zrange(self.action_queue_key, 0, -1, withscores=True)
            
            if not actions:
                return
            
            logger.info(f"Processing {len(actions)} pending actions")
            
            for action_json, score in actions:
                try:
                    # Parse action data
                    action_data = json.loads(action_json)
                    device = action_data.get("device")
                    action_type = action_data.get("action_type")
                    parameters = action_data.get("parameters", {})
                    priority = action_data.get("priority", 1)
                    
                    logger.info(f"Processing action: {action_type} for {device} (priority: {priority})")
                    
                    # Execute the action
                    success = await self._execute_action(action_data)
                    
                    if success:
                        # Remove from queue
                        await r.zrem(self.action_queue_key, action_json)
                        logger.info(f"Action {action_type} for {device} executed successfully")
                        
                        # Send WebSocket update
                        await self._send_automation_update(device, action_data, "completed")
                    else:
                        logger.error(f"Failed to execute action {action_type} for {device}")
                        # Keep in queue for retry (could implement retry logic here)
                        
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid action JSON: {e}")
                    # Remove invalid action
                    await r.zrem(self.action_queue_key, action_json)
                except Exception as e:
                    logger.error(f"Error processing action: {e}")
                    
        except Exception as e:
            logger.error(f"Error processing pending actions: {e}")
    
    async def _execute_action(self, action_data: Dict[str, Any]) -> bool:
        """Execute a single automation action"""
        try:
            device = action_data.get("device")
            action_type = action_data.get("action_type")
            parameters = action_data.get("parameters", {})
            
            # Map action types to automation service
            if action_type == "congestion_mitigation":
                await automation_service.queue_action(
                    ActionType.CONGESTION_MITIGATION,
                    device,
                    parameters
                )
            elif action_type == "bandwidth_optimization":
                await automation_service.queue_action(
                    ActionType.BANDWIDTH_ADJUSTMENT,
                    device,
                    parameters
                )
            elif action_type == "latency_optimization":
                await automation_service.queue_action(
                    ActionType.QOS_UPDATE,
                    device,
                    parameters
                )
            elif action_type == "anomaly_investigation":
                await automation_service.queue_action(
                    ActionType.MONITORING_ENABLE,
                    device,
                    parameters
                )
            else:
                # Default to general action
                await automation_service.queue_action(
                    ActionType.CONFIG_UPDATE,
                    device,
                    parameters
                )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to execute action {action_type}: {e}")
            return False
    
    async def _send_automation_update(self, device: str, action_data: Dict[str, Any], status: str):
        """Send automation update via WebSocket"""
        try:
            update_data = {
                "action_type": action_data.get("action_type"),
                "status": status,
                "parameters": action_data.get("parameters"),
                "timestamp": datetime.now().isoformat()
            }
            
            # Send via WebSocket manager
            await ws_manager.send_automation_update(device, update_data)
            
            # Send via broadcaster
            await broadcaster.emit_action_executed(
                device,
                action_data.get("action_type"),
                update_data
            )
            
        except Exception as e:
            logger.error(f"Failed to send automation update: {e}")
    
    async def add_action(self, action_data: Dict[str, Any]) -> bool:
        """Add a new action to the Redis queue"""
        try:
            r = await self._get_redis_connection()
            if not r:
                return False
            
            # Add timestamp if not present
            if "timestamp" not in action_data:
                action_data["timestamp"] = datetime.now().isoformat()
            
            # Calculate priority score
            priority = action_data.get("priority", 1)
            score = float(priority) + (datetime.now().timestamp() / 1000000)
            
            # Add to queue
            await r.zadd(self.action_queue_key, {json.dumps(action_data): score})
            
            logger.info(f"Added action to queue: {action_data.get('action_type')} for {action_data.get('device')}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add action to queue: {e}")
            return False
    
    async def get_queue_status(self) -> Dict[str, Any]:
        """Get current queue status"""
        try:
            r = await self._get_redis_connection()
            if not r:
                return {"error": "Redis connection failed"}
            
            # Get queue size
            queue_size = await r.zcard(self.action_queue_key)
            
            # Get pending actions
            actions = await r.zrange(self.action_queue_key, 0, -1, withscores=True)
            
            pending_actions = []
            for action_json, score in actions:
                try:
                    action_data = json.loads(action_json)
                    action_data["priority_score"] = score
                    pending_actions.append(action_data)
                except json.JSONDecodeError:
                    continue
            
            return {
                "queue_size": queue_size,
                "pending_actions": pending_actions,
                "processor_running": self.running,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get queue status: {e}")
            return {"error": str(e)}

# Global instance
redis_processor = RedisActionProcessor()

async def initialize_redis_processor():
    """Initialize the Redis action processor"""
    await redis_processor.start()
    logger.info("Redis action processor initialized")

async def stop_redis_processor():
    """Stop the Redis action processor"""
    await redis_processor.stop()
    logger.info("Redis action processor stopped")
