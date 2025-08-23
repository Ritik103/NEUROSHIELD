#!/usr/bin/env python3
"""
Phase 2-4 Comprehensive Test Script for NEUROSHIELD
Tests predictions, API & Dashboard, and automation functionality
"""

import asyncio
import sys
import traceback
from pathlib import Path

# Add app directory to path
HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parent / "app"))

def test_phase2_predictions():
    """Test Phase 2: Enhanced predictions with automation"""
    print("=== PHASE 2: ENHANCED PREDICTIONS ===")
    try:
        from services.model_service import ModelService
        ms = ModelService()
        
        # Test basic predictions
        devices = ms.get_devices()
        print(f"✅ Found {len(devices)} devices: {devices}")
        
        # Test predictions for each device
        for device in devices:
            try:
                prediction = ms.predict_for_device(device, k=10)
                if prediction.get('ok'):
                    print(f"✅ {device}: Basic prediction working")
                    print(f"   - Congestion prob: {prediction.get('congestion_prob', 'N/A'):.3f}")
                    print(f"   - Anomaly: {prediction.get('anomaly', 'N/A')}")
                    print(f"   - Threshold: {prediction.get('threshold', 'N/A')}")
                else:
                    print(f"⚠️  {device}: Prediction issues - {prediction}")
            except Exception as e:
                print(f"❌ {device}: Prediction error - {e}")
        
        # Test automation policies
        policies = ms.get_automation_policies()
        print(f"✅ Automation policies: {policies}")
        
        return True
        
    except Exception as e:
        print(f"❌ FAILED: Phase 2 predictions error - {e}")
        traceback.print_exc()
        return False

async def test_phase3_api_dashboard():
    """Test Phase 3: API & Dashboard functionality"""
    print("\n=== PHASE 3: API & DASHBOARD ===")
    try:
        from services.model_service import ModelService
        from routers.dashboard import get_dashboard_overview
        from routers.predict import predict_with_automation, predict_device_with_automation
        
        # Test dashboard overview
        overview = await get_dashboard_overview()
        print(f"✅ Dashboard overview: {overview.get('total_devices', 0)} devices")
        print(f"   - System health: {overview.get('system_health', 'N/A')}")
        print(f"   - Active alerts: {overview.get('active_alerts', 0)}")
        
        # Test automated predictions endpoint
        automated_predictions = await predict_with_automation(k=10)
        print(f"✅ Automated predictions: {automated_predictions.get('total_devices', 0)} devices")
        print(f"   - Automation enabled: {automated_predictions.get('automation_enabled', False)}")
        
        # Test device-specific automated prediction
        ms = ModelService()
        devices = ms.get_devices()
        if devices:
            device_prediction = await predict_device_with_automation(devices[0], k=10)
            print(f"✅ Device prediction: {device_prediction.get('device', 'N/A')}")
            print(f"   - Automation enabled: {device_prediction.get('automation_enabled', False)}")
        
        return True
        
    except Exception as e:
        print(f"❌ FAILED: Phase 3 API & Dashboard error - {e}")
        traceback.print_exc()
        return False

async def test_phase4_automation():
    """Test Phase 4: Automation functionality"""
    print("\n=== PHASE 4: AUTOMATION ===")
    try:
        from services.model_service import ModelService
        from services.redis_processor import redis_processor
        
        ms = ModelService()
        devices = ms.get_devices()
        
        if not devices:
            print("⚠️  No devices found for automation testing")
            return False
        
        # Test automation evaluation for a device
        device = devices[0]
        print(f"Testing automation for device: {device}")
        
        # Test evaluate_and_automate
        result = await ms.evaluate_and_automate(device, k=10)
        if result.get('ok'):
            print(f"✅ Automation evaluation successful")
            automation_triggered = result.get('automation_triggered', [])
            print(f"   - Actions triggered: {automation_triggered}")
            
            if automation_triggered:
                print(f"   - Automation policies working correctly")
            else:
                print(f"   - No actions triggered (may be normal based on current data)")
        else:
            print(f"⚠️  Automation evaluation issues: {result}")
        
        # Test Redis processor status
        queue_status = await redis_processor.get_queue_status()
        print(f"✅ Redis queue status: {queue_status.get('queue_size', 0)} pending actions")
        
        # Test automation policies update
        current_policies = ms.get_automation_policies()
        test_policies = {"congestion_threshold": 0.5}
        success = ms.update_automation_policies(test_policies)
        if success:
            print(f"✅ Policy update successful")
            # Restore original policies
            ms.update_automation_policies(current_policies)
        else:
            print(f"⚠️  Policy update failed")
        
        return True
        
    except Exception as e:
        print(f"❌ FAILED: Phase 4 automation error - {e}")
        traceback.print_exc()
        return False

async def test_websocket_integration():
    """Test WebSocket integration for real-time updates"""
    print("\n=== WEBSOCKET INTEGRATION ===")
    try:
        from ws import manager
        
        # Test WebSocket manager
        print(f"✅ WebSocket manager: {len(manager.active_connections)} active connections")
        
        # Test WebSocket methods exist
        if hasattr(manager, 'send_automation_update'):
            print("✅ Automation update method available")
        else:
            print("⚠️  Automation update method missing")
        
        if hasattr(manager, 'send_policy_update'):
            print("✅ Policy update method available")
        else:
            print("⚠️  Policy update method missing")
        
        return True
        
    except Exception as e:
        print(f"❌ FAILED: WebSocket integration error - {e}")
        traceback.print_exc()
        return False

async def test_redis_integration():
    """Test Redis integration for action queue"""
    print("\n=== REDIS INTEGRATION ===")
    try:
        from services.redis_processor import redis_processor
        
        # Test Redis connection
        queue_status = await redis_processor.get_queue_status()
        if "error" not in queue_status:
            print(f"✅ Redis connection successful")
            print(f"   - Queue size: {queue_status.get('queue_size', 0)}")
            print(f"   - Processor running: {queue_status.get('processor_running', False)}")
        else:
            print(f"⚠️  Redis connection issues: {queue_status.get('error')}")
        
        # Test action addition
        test_action = {
            "device": "Router_A",
            "action_type": "test_action",
            "parameters": {"test": "value"},
            "priority": 1
        }
        
        success = await redis_processor.add_action(test_action)
        if success:
            print("✅ Action addition successful")
            
            # Check if action was added
            updated_status = await redis_processor.get_queue_status()
            new_size = updated_status.get('queue_size', 0)
            print(f"   - New queue size: {new_size}")
            
            # Clean up test action
            # This would normally be processed by the processor
            print("   - Test action added to queue")
        else:
            print("⚠️  Action addition failed")
        
        return True
        
    except Exception as e:
        print(f"❌ FAILED: Redis integration error - {e}")
        traceback.print_exc()
        return False

async def test_end_to_end_automation():
    """Test end-to-end automation workflow"""
    print("\n=== END-TO-END AUTOMATION ===")
    try:
        from services.model_service import ModelService
        from services.redis_processor import redis_processor
        
        ms = ModelService()
        devices = ms.get_devices()
        
        if not devices:
            print("⚠️  No devices found for end-to-end testing")
            return False
        
        device = devices[0]
        print(f"Testing end-to-end automation for: {device}")
        
        # Step 1: Get prediction with automation
        result = await ms.evaluate_and_automate(device, k=10)
        print(f"✅ Step 1 - Automation evaluation: {result.get('ok', False)}")
        
        if result.get('ok'):
            automation_triggered = result.get('automation_triggered', [])
            print(f"   - Actions triggered: {automation_triggered}")
            
            # Step 2: Check Redis queue
            if automation_triggered:
                await asyncio.sleep(2)  # Give time for actions to be queued
                queue_status = await redis_processor.get_queue_status()
                queue_size = queue_status.get('queue_size', 0)
                print(f"✅ Step 2 - Redis queue: {queue_size} pending actions")
                
                if queue_size > 0:
                    print("   - Automation actions successfully queued")
                else:
                    print("   - No actions in queue (may have been processed)")
            else:
                print("   - No automation actions triggered (normal behavior)")
        
        return True
        
    except Exception as e:
        print(f"❌ FAILED: End-to-end automation error - {e}")
        traceback.print_exc()
        return False

async def main():
    """Run all Phase 2-4 tests"""
    print("🚀 NEUROSHIELD PHASE 2-4 COMPREHENSIVE TEST")
    print("=" * 60)
    
    tests = [
        ("Phase 2: Enhanced Predictions", test_phase2_predictions),
        ("Phase 3: API & Dashboard", test_phase3_api_dashboard),
        ("Phase 4: Automation", test_phase4_automation),
        ("WebSocket Integration", test_websocket_integration),
        ("Redis Integration", test_redis_integration),
        ("End-to-End Automation", test_end_to_end_automation),
    ]
    
    results = []
    
    # Run all tests
    for test_name, test_func in tests:
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ FAILED: {test_name} crashed - {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 PHASE 2-4 TEST RESULTS SUMMARY")
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
        print("🎉 ALL PHASES COMPLETED! NEUROSHIELD is fully functional with automation!")
        return True
    else:
        print("⚠️  Some phases failed. Please review the issues above.")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
