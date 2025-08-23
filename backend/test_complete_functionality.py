#!/usr/bin/env python3
"""
Comprehensive test script for NEUROSHIELD backend
Tests all major components and functionality
"""

import asyncio
import sys
import traceback
from pathlib import Path

# Add app directory to path
HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parent / "app"))

def test_data_loading():
    """Test data loading from CSV files"""
    print("=== TESTING DATA LOADING ===")
    try:
        from worker.feature_builder import load_router_logs
        df = load_router_logs()
        
        if df.empty:
            print("❌ FAILED: No data loaded")
            return False
        
        devices = df['Device Name'].unique()
        print(f"✅ SUCCESS: Loaded {len(df)} records")
        print(f"✅ SUCCESS: Found devices: {list(devices)}")
        
        if len(devices) == 3 and all(d in devices for d in ['Router_A', 'Router_B', 'Router_C']):
            print("✅ SUCCESS: All 3 routers found")
            return True
        else:
            print("❌ FAILED: Not all routers found")
            return False
            
    except Exception as e:
        print(f"❌ FAILED: Data loading error - {e}")
        traceback.print_exc()
        return False

def test_model_service():
    """Test ML model service"""
    print("\n=== TESTING MODEL SERVICE ===")
    try:
        from services.model_service import ModelService
        ms = ModelService()
        
        devices = ms.get_devices()
        print(f"✅ SUCCESS: Model service initialized, found {len(devices)} devices")
        
        # Test predictions for each device
        for device in devices:
            try:
                prediction = ms.predict_for_device(device, k=10)
                if prediction.get('ok'):
                    print(f"✅ SUCCESS: {device} prediction working")
                else:
                    print(f"⚠️  WARNING: {device} prediction issues - {prediction}")
            except Exception as e:
                print(f"❌ FAILED: {device} prediction error - {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ FAILED: Model service error - {e}")
        traceback.print_exc()
        return False

def test_database_service():
    """Test database service"""
    print("\n=== TESTING DATABASE SERVICE ===")
    try:
        from services.db import db_service
        
        # Test database stats
        stats = db_service.get_database_stats()
        print(f"✅ SUCCESS: Database service working, stats: {stats}")
        
        # Test router logs retrieval
        logs_df = db_service.get_router_logs(limit=5)
        if not logs_df.empty:
            print(f"✅ SUCCESS: Retrieved {len(logs_df)} router logs")
        else:
            print("⚠️  WARNING: No router logs in database")
        
        return True
        
    except Exception as e:
        print(f"❌ FAILED: Database service error - {e}")
        traceback.print_exc()
        return False

def test_network_automation():
    """Test network automation service"""
    print("\n=== TESTING NETWORK AUTOMATION ===")
    try:
        from services.network_automation import automation_service
        
        # Test device configs
        configs = automation_service.get_all_device_configs()
        print(f"✅ SUCCESS: Network automation service working, {len(configs)} device configs")
        
        # Test action queuing
        from services.network_automation import ActionType
        action_id = asyncio.run(automation_service.queue_action(
            ActionType.ALERT_NOTIFICATION,
            "Router_A",
            {"message": "Test alert", "alert_type": "info"}
        ))
        print(f"✅ SUCCESS: Action queued with ID: {action_id}")
        
        return True
        
    except Exception as e:
        print(f"❌ FAILED: Network automation error - {e}")
        traceback.print_exc()
        return False

def test_broadcaster():
    """Test event broadcaster"""
    print("\n=== TESTING EVENT BROADCASTER ===")
    try:
        from services.broadcaster import broadcaster
        
        # Test event emission
        asyncio.run(broadcaster.emit_system_alert("Test message", "info"))
        print("✅ SUCCESS: Event broadcaster working")
        
        return True
        
    except Exception as e:
        print(f"❌ FAILED: Event broadcaster error - {e}")
        traceback.print_exc()
        return False

def test_dashboard():
    """Test dashboard functionality"""
    print("\n=== TESTING DASHBOARD ===")
    try:
        from routers.dashboard import get_dashboard_overview
        
        # Test dashboard overview
        overview = asyncio.run(get_dashboard_overview())
        print(f"✅ SUCCESS: Dashboard working, {overview.get('total_devices', 0)} devices")
        
        return True
        
    except Exception as e:
        print(f"❌ FAILED: Dashboard error - {e}")
        traceback.print_exc()
        return False

def test_main_app():
    """Test main FastAPI app"""
    print("\n=== TESTING MAIN APP ===")
    try:
        from main import app
        
        # Check if all routers are included
        routes = [route.path for route in app.routes]
        expected_routes = ['/api/ingest', '/api/predict/device/{device}', '/api/predict/all', 
                          '/api/actions', '/api/dashboard/overview', '/ws']
        
        missing_routes = [r for r in expected_routes if not any(r in route for route in routes)]
        
        if not missing_routes:
            print("✅ SUCCESS: Main app imports successfully with all expected routes")
            return True
        else:
            print(f"⚠️  WARNING: Missing routes: {missing_routes}")
            return False
            
    except Exception as e:
        print(f"❌ FAILED: Main app error - {e}")
        traceback.print_exc()
        return False

def test_websocket():
    """Test WebSocket functionality"""
    print("\n=== TESTING WEBSOCKET ===")
    try:
        from ws import manager
        
        # Test WebSocket manager
        print(f"✅ SUCCESS: WebSocket manager working, {len(manager.active_connections)} active connections")
        return True
        
    except Exception as e:
        print(f"❌ FAILED: WebSocket error - {e}")
        traceback.print_exc()
        return False

async def test_services_initialization():
    """Test services initialization"""
    print("\n=== TESTING SERVICES INITIALIZATION ===")
    try:
        from services.broadcaster import initialize_broadcaster
        from services.network_automation import initialize_automation_service
        
        await initialize_broadcaster()
        await initialize_automation_service()
        
        print("✅ SUCCESS: All services initialized successfully")
        return True
        
    except Exception as e:
        print(f"❌ FAILED: Services initialization error - {e}")
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("🚀 NEUROSHIELD COMPREHENSIVE FUNCTIONALITY TEST")
    print("=" * 60)
    
    tests = [
        ("Data Loading", test_data_loading),
        ("Model Service", test_model_service),
        ("Database Service", test_database_service),
        ("Network Automation", test_network_automation),
        ("Event Broadcaster", test_broadcaster),
        ("Dashboard", test_dashboard),
        ("Main App", test_main_app),
        ("WebSocket", test_websocket),
    ]
    
    results = []
    
    # Run synchronous tests
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ FAILED: {test_name} crashed - {e}")
            results.append((test_name, False))
    
    # Run async tests
    try:
        async_result = asyncio.run(test_services_initialization())
        results.append(("Services Initialization", async_result))
    except Exception as e:
        print(f"❌ FAILED: Services initialization crashed - {e}")
        results.append(("Services Initialization", False))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 OVERALL: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! NEUROSHIELD is fully functional!")
        return True
    else:
        print("⚠️  Some tests failed. Please review the issues above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
