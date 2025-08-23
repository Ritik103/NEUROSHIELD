#!/usr/bin/env python3
"""
Test script to run server in foreground to see error messages
"""

import uvicorn
import sys
import traceback

def test_server_startup():
    """Test server startup in foreground"""
    print("🚀 Testing server startup in foreground...")
    
    try:
        from app.main_fixed import app
        print("✅ App imported successfully")
        print("📋 Routes:", [route.path for route in app.routes])
        
        print("\n🌐 Starting server on 127.0.0.1:8000...")
        print("Press Ctrl+C to stop")
        
        uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
        
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = test_server_startup()
    sys.exit(0 if success else 1)

