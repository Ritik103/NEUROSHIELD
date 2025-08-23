#!/usr/bin/env python3
"""
Debug script to isolate server startup issues
"""

import asyncio
import sys
import traceback

def test_basic_imports():
    """Test basic imports without starting server"""
    print("🔍 Testing basic imports...")
    
    try:
        from app.main import app
        print("✅ app.main imported successfully")
        return True
    except Exception as e:
        print(f"❌ app.main import failed: {e}")
        traceback.print_exc()
        return False

def test_simple_fastapi():
    """Test simple FastAPI without our app"""
    print("\n🔍 Testing simple FastAPI...")
    
    try:
        from fastapi import FastAPI
        import uvicorn
        
        app = FastAPI()
        
        @app.get("/")
        def root():
            return {"message": "test"}
        
        print("✅ Simple FastAPI created successfully")
        return True
    except Exception as e:
        print(f"❌ Simple FastAPI failed: {e}")
        traceback.print_exc()
        return False

def test_our_app_creation():
    """Test our app creation without starting server"""
    print("\n🔍 Testing our app creation...")
    
    try:
        from app.main import app
        print(f"✅ Our app created successfully")
        print(f"📋 Routes: {[route.path for route in app.routes]}")
        return True
    except Exception as e:
        print(f"❌ Our app creation failed: {e}")
        traceback.print_exc()
        return False

async def test_service_initialization():
    """Test service initialization"""
    print("\n🔍 Testing service initialization...")
    
    try:
        from app.services.broadcaster import initialize_broadcaster
        from app.services.network_automation import initialize_automation_service
        from app.services.redis_processor import initialize_redis_processor
        
        print("  Initializing broadcaster...")
        await initialize_broadcaster()
        print("  ✅ Broadcaster initialized")
        
        print("  Initializing automation service...")
        await initialize_automation_service()
        print("  ✅ Automation service initialized")
        
        print("  Initializing redis processor...")
        await initialize_redis_processor()
        print("  ✅ Redis processor initialized")
        
        return True
    except Exception as e:
        print(f"❌ Service initialization failed: {e}")
        traceback.print_exc()
        return False

def test_server_startup():
    """Test actual server startup"""
    print("\n🔍 Testing server startup...")
    
    try:
        from app.main import app
        import uvicorn
        
        print("  Starting server on localhost:8000...")
        # This should show us the actual error
        uvicorn.run(app, host="localhost", port=8000, log_level="info")
        return True
    except Exception as e:
        print(f"❌ Server startup failed: {e}")
        traceback.print_exc()
        return False

def main():
    """Main debug function"""
    print("🚀 NEUROSHIELD Backend - Server Startup Issue Debug")
    print("=" * 60)
    
    # Test 1: Basic imports
    if not test_basic_imports():
        print("\n❌ Basic imports failed. Cannot proceed.")
        return False
    
    # Test 2: Simple FastAPI
    if not test_simple_fastapi():
        print("\n❌ Simple FastAPI failed.")
        return False
    
    # Test 3: Our app creation
    if not test_our_app_creation():
        print("\n❌ Our app creation failed.")
        return False
    
    # Test 4: Service initialization
    if not asyncio.run(test_service_initialization()):
        print("\n❌ Service initialization failed.")
        return False
    
    # Test 5: Server startup
    print("\n🎯 Testing actual server startup...")
    test_server_startup()
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

