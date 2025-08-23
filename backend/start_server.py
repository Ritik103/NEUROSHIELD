#!/usr/bin/env python3
"""
Simple server startup script for debugging
"""

import uvicorn
import logging
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Start the FastAPI server"""
    try:
        logger.info("🚀 Starting NEUROSHIELD Backend Server...")
        
        # Test imports
        logger.info("📦 Testing imports...")
        try:
            from app.main import app
            logger.info("✅ App imported successfully")
        except Exception as e:
            logger.error(f"❌ Failed to import app: {e}")
            return 1
        
        # Test service imports
        logger.info("🔧 Testing service imports...")
        try:
            from app.services.model_service import ModelService
            from app.services.db import db_service
            from app.services.broadcaster import broadcaster
            from app.services.network_automation import automation_service
            logger.info("✅ All services imported successfully")
        except Exception as e:
            logger.error(f"❌ Failed to import services: {e}")
            return 1
        
        # Test model service
        logger.info("🤖 Testing model service...")
        try:
            svc = ModelService()
            devices = svc.get_devices()
            logger.info(f"✅ Model service working, found {len(devices)} devices: {devices}")
        except Exception as e:
            logger.error(f"❌ Model service failed: {e}")
            return 1
        
        # Start server
        logger.info("🌐 Starting FastAPI server on http://localhost:8000")
        logger.info("📚 API documentation available at http://localhost:8000/docs")
        
        uvicorn.run(
            "app.main:app",
            host="0.0.0.0",
            port=8000,
            reload=False,
            log_level="info",
            access_log=True
        )
        
    except KeyboardInterrupt:
        logger.info("🛑 Server stopped by user")
        return 0
    except Exception as e:
        logger.error(f"❌ Server failed to start: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
