#!/usr/bin/env python3
"""
NEUROSHIELD Startup Script (Redis-Free for Testing)
Starts the FastAPI server with minimal Redis dependency
"""

import uvicorn
import asyncio
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def initialize_services():
    """Initialize core NEUROSHIELD services without Redis"""
    try:
        logger.info("🚀 Initializing NEUROSHIELD services (Redis-free mode)...")
        
        # Initialize broadcaster (without Redis)
        from app.services.broadcaster import initialize_broadcaster
        await initialize_broadcaster()
        logger.info("✅ Event broadcaster initialized")
        
        # Initialize network automation
        from app.services.network_automation import initialize_automation_service
        await initialize_automation_service()
        logger.info("✅ Network automation service initialized")
        
        # Initialize database
        from app.services.db import db_service
        logger.info("✅ Database service initialized")
        
        # Test data loading
        from worker.feature_builder import load_router_logs
        df = load_router_logs()
        devices = df['Device Name'].unique()
        logger.info(f"✅ Data loaded: {len(df)} records from {len(devices)} devices: {list(devices)}")
        
        # Test model service
        from app.services.model_service import ModelService
        ms = ModelService()
        devices = ms.get_devices()
        logger.info(f"✅ Model service: {len(devices)} devices available")
        
        logger.info("🎉 Core services initialized successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Service initialization failed: {e}")
        return False

def main():
    """Main startup function"""
    logger.info("🚀 Starting NEUROSHIELD Backend (Redis-free mode)...")
    
    # Initialize services
    success = asyncio.run(initialize_services())
    if not success:
        logger.error("Failed to initialize services. Exiting.")
        return
    
    # Start FastAPI server
    logger.info("🌐 Starting FastAPI server...")
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )

if __name__ == "__main__":
    main()
