#!/usr/bin/env python3
"""
Comprehensive real-time data simulation script for NEUROSHIELD
Simulates data from all 3 routers (A, B, C) with realistic patterns
"""

import asyncio
import json
import logging
import random
import time
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
import requests
import sys
import os

# Add app directory to path for imports
HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parent / "app"))

from services.db import db_service
from services.broadcaster import broadcaster, EventType
from services.model_service import ModelService

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RouterDataSimulator:
    def __init__(self, api_base_url: str = "http://localhost:8000"):
        self.api_base_url = api_base_url
        self.running = False
        self.devices = ["Router_A", "Router_B", "Router_C"]
        
        # Load historical data to understand patterns
        self.historical_data = self._load_historical_data()
        
        # Simulation parameters
        self.base_patterns = {
            "Router_A": {"peak_hours": [9, 14, 18], "base_traffic": 45, "volatility": 0.3},
            "Router_B": {"peak_hours": [8, 12, 20], "base_traffic": 35, "volatility": 0.4},
            "Router_C": {"peak_hours": [10, 16, 22], "base_traffic": 55, "volatility": 0.2}
        }
        
        # IP pools for each router
        self.ip_pools = {
            "Router_A": {
                "source": ["192.168.1.{}".format(i) for i in range(1, 200)],
                "dest": ["192.168.2.{}".format(i) for i in range(1, 250)]
            },
            "Router_B": {
                "source": ["192.168.3.{}".format(i) for i in range(1, 200)],
                "dest": ["192.168.4.{}".format(i) for i in range(1, 250)]
            },
            "Router_C": {
                "source": ["192.168.5.{}".format(i) for i in range(1, 200)],
                "dest": ["192.168.6.{}".format(i) for i in range(1, 250)]
            }
        }
        
        # Simulation state
        self.congestion_events = {}  # Track congestion per device
        self.anomaly_counters = {}   # Track anomalies per device
        
        for device in self.devices:
            self.congestion_events[device] = 0
            self.anomaly_counters[device] = 0

    def _load_historical_data(self) -> dict:
        """Load historical data to understand patterns"""
        data_dir = HERE.parent.parent / "datasets"
        historical = {}
        
        for device in self.devices:
            csv_file = data_dir / f"{device}_router_log_15_days.csv"
            if csv_file.exists():
                try:
                    df = pd.read_csv(csv_file)
                    historical[device] = df
                    logger.info(f"Loaded {len(df)} historical records for {device}")
                except Exception as e:
                    logger.error(f"Error loading historical data for {device}: {e}")
                    historical[device] = pd.DataFrame()
            else:
                logger.warning(f"Historical data file not found: {csv_file}")
                historical[device] = pd.DataFrame()
        
        return historical

    def _get_time_based_multiplier(self, device: str, current_hour: int) -> float:
        """Get traffic multiplier based on time of day and device patterns"""
        patterns = self.base_patterns[device]
        peak_hours = patterns["peak_hours"]
        
        # Base multiplier
        multiplier = 1.0
        
        # Peak hour effects
        for peak_hour in peak_hours:
            distance = min(abs(current_hour - peak_hour), 24 - abs(current_hour - peak_hour))
            if distance <= 2:  # Within 2 hours of peak
                multiplier += (2 - distance) * 0.3
        
        # Night time reduction (22:00 - 06:00)
        if current_hour >= 22 or current_hour <= 6:
            multiplier *= 0.6
        
        # Weekend effect (assume random weekend behavior)
        if random.random() < 0.3:  # 30% chance of weekend-like behavior
            multiplier *= random.uniform(0.7, 1.2)
        
        return max(0.3, min(2.0, multiplier))  # Clamp between 0.3 and 2.0

    def _generate_realistic_log_entry(self, device: str, timestamp: datetime) -> dict:
        """Generate a realistic log entry for a device"""
        patterns = self.base_patterns[device]
        current_hour = timestamp.hour
        
        # Time-based traffic multiplier
        time_multiplier = self._get_time_based_multiplier(device, current_hour)
        
        # Base traffic with time variation
        base_traffic = patterns["base_traffic"] * time_multiplier
        volatility = patterns["volatility"]
        
        # Add random variation
        traffic_variation = random.gauss(0, volatility)
        traffic_volume = max(5, base_traffic + traffic_variation * base_traffic)
        
        # Bandwidth allocation (typically 100 MB/s)
        bandwidth_allocated = 100.0
        
        # Bandwidth used based on traffic volume with some efficiency
        efficiency = random.uniform(0.85, 1.15)
        bandwidth_used = min(bandwidth_allocated, traffic_volume * efficiency)
        
        # Latency correlation with traffic (higher traffic = higher latency generally)
        base_latency = 25
        traffic_factor = (traffic_volume / patterns["base_traffic"]) - 1
        latency = base_latency + traffic_factor * 15 + random.gauss(0, 5)
        latency = max(5, min(100, latency))  # Clamp between 5-100ms
        
        # Congestion detection (bandwidth usage > 85% with high latency)
        utilization = bandwidth_used / bandwidth_allocated
        congestion_threshold = 0.85
        latency_threshold = 45
        
        # Introduce occasional congestion events
        congestion_chance = 0.05  # 5% base chance
        if utilization > 0.8:
            congestion_chance += 0.1  # Increase chance when utilization is high
        if latency > 40:
            congestion_chance += 0.05  # Increase chance when latency is high
        
        is_congested = random.random() < congestion_chance
        if is_congested:
            self.congestion_events[device] += 1
            # Make congestion more obvious
            bandwidth_used = min(bandwidth_allocated, bandwidth_used * random.uniform(1.1, 1.3))
            latency = max(latency, random.uniform(50, 80))
        
        congestion_flag = "Yes" if (utilization > congestion_threshold and latency > latency_threshold) or is_congested else "No"
        
        # Generate log text
        if congestion_flag == "Yes":
            log_texts = [
                "High utilization, nearing bandwidth limit",
                "Congestion detected, consider traffic shaping",
                "High latency and bandwidth usage detected",
                "Network congestion warning"
            ]
            log_text = random.choice(log_texts)
        else:
            log_texts = [
                "Normal operation",
                "Traffic flowing normally",
                "Optimal performance",
                "Standard network operation"
            ]
            log_text = random.choice(log_texts)
        
        # Random IPs from device pools
        source_ip = random.choice(self.ip_pools[device]["source"])
        dest_ip = random.choice(self.ip_pools[device]["dest"])
        
        return {
            "Timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "Device Name": device,
            "Source IP": source_ip,
            "Destination IP": dest_ip,
            "Traffic Volume (MB/s)": round(traffic_volume, 2),
            "Latency (ms)": round(latency, 2),
            "Bandwidth Allocated (MB/s)": bandwidth_allocated,
            "Bandwidth Used (MB/s)": round(bandwidth_used, 2),
            "Congestion Flag": congestion_flag,
            "Log Text": log_text
        }

    async def _send_logs_to_api(self, logs: list) -> bool:
        """Send logs to the ingestion API"""
        try:
            url = f"{self.api_base_url}/api/ingest"
            response = requests.post(url, json=logs, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Successfully sent {result.get('items', 0)} log entries")
                return True
            else:
                logger.error(f"API error: {response.status_code} - {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending logs: {e}")
            return False

    async def _generate_predictions_and_events(self):
        """Generate predictions and emit events for interesting conditions"""
        try:
            from services.model_service import ModelService
            model_service = ModelService()
            
            for device in self.devices:
                try:
                    # Get prediction
                    prediction = model_service.predict_for_device(device, k=5)
                    
                    if prediction.get("ok"):
                        congestion_prob = prediction.get("congestion_prob", 0)
                        anomaly = prediction.get("anomaly", 0)
                        
                        # Store prediction in database
                        db_service.insert_prediction(
                            device, 
                            datetime.now().isoformat(),
                            prediction
                        )
                        
                        # Emit events for significant conditions
                        if congestion_prob > 0.7:
                            await broadcaster.emit_congestion_detected(
                                device, congestion_prob, prediction
                            )
                            logger.warning(f"High congestion probability for {device}: {congestion_prob:.2f}")
                        
                        if anomaly == 1:
                            await broadcaster.emit_anomaly_detected(
                                device, 1.0, prediction
                            )
                            logger.warning(f"Anomaly detected for {device}")
                        
                        # Update device status
                        db_service.update_device_status(
                            device, "active", 
                            metrics={"congestion_prob": congestion_prob, "anomaly": anomaly},
                            prediction=prediction
                        )
                
                except Exception as e:
                    logger.error(f"Error generating prediction for {device}: {e}")
        
        except ImportError as e:
            logger.warning(f"Model service not available: {e}")

    async def simulate_batch(self, batch_size: int = 6, interval_minutes: int = 5) -> bool:
        """Simulate a batch of logs for all devices"""
        current_time = datetime.now()
        logs = []
        
        # Generate logs for each device (2 entries per device per batch)
        for device in self.devices:
            for i in range(batch_size // len(self.devices)):
                log_time = current_time - timedelta(minutes=i * interval_minutes)
                log_entry = self._generate_realistic_log_entry(device, log_time)
                logs.append(log_entry)
        
        # Send to API
        success = await self._send_logs_to_api(logs)
        
        if success:
            # Store in database as backup
            try:
                db_service.batch_insert_router_logs(logs)
                logger.info(f"Batch of {len(logs)} logs stored in database")
            except Exception as e:
                logger.error(f"Error storing logs in database: {e}")
            
            # Generate predictions and events
            await self._generate_predictions_and_events()
        
        return success

    async def simulate_continuous(self, interval_seconds: int = 30, batch_size: int = 6):
        """Run continuous simulation"""
        logger.info(f"Starting continuous simulation with {interval_seconds}s intervals")
        self.running = True
        
        iteration = 0
        consecutive_failures = 0
        
        while self.running:
            try:
                iteration += 1
                logger.info(f"Simulation iteration {iteration}")
                
                success = await self.simulate_batch(batch_size)
                
                if success:
                    consecutive_failures = 0
                    # Emit metrics update
                    try:
                        await broadcaster.emit_metrics_update({
                            "simulation_iteration": iteration,
                            "timestamp": datetime.now().isoformat(),
                            "devices_active": len(self.devices),
                            "congestion_events": sum(self.congestion_events.values()),
                            "anomaly_events": sum(self.anomaly_counters.values())
                        })
                    except Exception as e:
                        logger.warning(f"Error emitting metrics: {e}")
                else:
                    consecutive_failures += 1
                    if consecutive_failures >= 5:
                        logger.error("Too many consecutive failures, stopping simulation")
                        break
                
                # Log statistics every 10 iterations
                if iteration % 10 == 0:
                    logger.info(f"Simulation stats after {iteration} iterations:")
                    for device in self.devices:
                        logger.info(f"  {device}: {self.congestion_events[device]} congestion events")
                
                # Wait for next iteration
                await asyncio.sleep(interval_seconds)
                
            except KeyboardInterrupt:
                logger.info("Simulation interrupted by user")
                break
            except Exception as e:
                logger.error(f"Error in simulation loop: {e}")
                consecutive_failures += 1
                await asyncio.sleep(interval_seconds)
        
        self.running = False
        logger.info("Simulation stopped")

    def stop(self):
        """Stop the simulation"""
        self.running = False

    async def initialize_data(self):
        """Initialize database with historical data from CSV files"""
        logger.info("Initializing database with historical data...")
        
        # This will trigger the CSV loading in feature_builder.py
        try:
            from services.model_service import ModelService
            model_service = ModelService()
            devices = model_service.get_devices()
            logger.info(f"Loaded data for devices: {devices}")
            
            # Verify data was loaded
            for device in devices:
                try:
                    prediction = model_service.predict_for_device(device, k=1)
                    if prediction.get("ok"):
                        logger.info(f"✓ {device}: Model working, last timestamp: {prediction.get('last_timestamp')}")
                    else:
                        logger.warning(f"⚠ {device}: Model issues - {prediction}")
                except Exception as e:
                    logger.error(f"✗ {device}: Error - {e}")
            
        except Exception as e:
            logger.error(f"Error initializing data: {e}")

async def main():
    """Main function to run the simulation"""
    import argparse
    
    parser = argparse.ArgumentParser(description="NEUROSHIELD Data Simulator")
    parser.add_argument("--api-url", default="http://localhost:8000", help="API base URL")
    parser.add_argument("--interval", type=int, default=30, help="Interval between batches (seconds)")
    parser.add_argument("--batch-size", type=int, default=6, help="Number of logs per batch")
    parser.add_argument("--init-only", action="store_true", help="Only initialize data, don't simulate")
    parser.add_argument("--one-shot", action="store_true", help="Run one batch and exit")
    
    args = parser.parse_args()
    
    simulator = RouterDataSimulator(api_base_url=args.api_url)
    
    # Initialize data
    await simulator.initialize_data()
    
    if args.init_only:
        logger.info("Data initialization complete. Exiting.")
        return
    
    if args.one_shot:
        logger.info("Running one-shot simulation...")
        success = await simulator.simulate_batch(args.batch_size)
        if success:
            logger.info("One-shot simulation completed successfully")
        else:
            logger.error("One-shot simulation failed")
        return
    
    # Initialize services
    try:
        from services.broadcaster import initialize_broadcaster
        await initialize_broadcaster()
        logger.info("Broadcaster initialized")
    except Exception as e:
        logger.warning(f"Could not initialize broadcaster: {e}")
    
    # Run continuous simulation
    try:
        await simulator.simulate_continuous(args.interval, args.batch_size)
    except KeyboardInterrupt:
        logger.info("Simulation interrupted")
    finally:
        simulator.stop()

if __name__ == "__main__":
    asyncio.run(main())
