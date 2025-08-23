#!/usr/bin/env python3
"""
Debug script to test server startup step by step
"""

import asyncio
import logging
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_imports():
    """Test all imports step by step"""
    print("🔍 Testing imports...")
    
    try:
        print("  Testing app.main...")
        from app.main import app
        print("  ✅ app.main imported successfully")
    except Exception as e:
        print(f"  ❌ app.main import failed: {e}")
        return False
    
    try:
        print("  Testing broadcaster...")
        from app.services.broadcaster import initialize_broadcaster
        print("  ✅ broadcaster imported successfully")
    except Exception as e:
        print(f"  ❌ broadcaster import failed: {e}")
        return False
    
    try:
        print("  Testing automation service...")
        from app.services.network_automation import initialize_automation_service
        print("  ✅ automation service imported successfully")
    except Exception as e:
        print(f"  ❌ automation service import failed: {e}")
        return False
    
    try:
        print("  Testing redis processor...")
        from app.services.redis_processor import initialize_redis_processor
        print("  ✅ redis processor imported successfully")
    except Exception as e:
        print(f"  ❌ redis processor import failed: {e}")
        return False
    
    try:
        print("  Testing WebSocket...")
        from app.ws import websocket_endpoint
        print("  ✅ WebSocket imported successfully")
    except Exception as e:
        print(f"  ❌ WebSocket import failed: {e}")
        return False
    
    return True

async def test_service_initialization():
    """Test service initialization"""
    print("\n🔧 Testing service initialization...")
    
    try:
        print("  Initializing broadcaster...")
        from app.services.broadcaster import initialize_broadcaster
        await initialize_broadcaster()
        print("  ✅ Broadcaster initialized")
    except Exception as e:
        print(f"  ❌ Broadcaster initialization failed: {e}")
        return False
    
    try:
        print("  Initializing automation service...")
        from app.services.network_automation import initialize_automation_service
        await initialize_automation_service()
        print("  ✅ Automation service initialized")
    except Exception as e:
        print(f"  ❌ Automation service initialization failed: {e}")
        return False
    
    try:
        print("  Initializing redis processor...")
        from app.services.redis_processor import initialize_redis_processor
        await initialize_redis_processor()
        print("  ✅ Redis processor initialized")
    except Exception as e:
        print(f"  ❌ Redis processor initialization failed: {e}")
        return False
    
    return True

async def test_fastapi_app():
    """Test FastAPI app creation"""
    print("\n🌐 Testing FastAPI app creation...")
    
    try:
        from app.main import app
        print(f"  ✅ FastAPI app created successfully")
        print(f"  📋 Routes: {[route.path for route in app.routes]}")
        return True
    except Exception as e:
        print(f"  ❌ FastAPI app creation failed: {e}")
        return False

async def test_model_service():
    """Test model service functionality"""
    print("\n🤖 Testing model service...")
    
    try:
        from app.services.model_service import ModelService
        svc = ModelService()
        devices = svc.get_devices()
        print(f"  ✅ Model service working, devices: {devices}")
        return True
    except Exception as e:
        print(f"  ❌ Model service failed: {e}")
        return False

async def main():
    """Main debug function"""
    print("🚀 NEUROSHIELD Backend - Server Startup Debug")
    print("=" * 50)
    
    # Test imports
    if not await test_imports():
        print("\n❌ Import tests failed. Cannot proceed.")
        return False
    
    # Test service initialization
    if not await test_service_initialization():
        print("\n❌ Service initialization failed.")
        return False
    
    # Test FastAPI app
    if not await test_fastapi_app():
        print("\n❌ FastAPI app creation failed.")
        return False
    
    # Test model service
    if not await test_model_service():
        print("\n❌ Model service test failed.")
        return False
    
    print("\n🎉 All tests passed! Server should be able to start.")
    return True

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)

