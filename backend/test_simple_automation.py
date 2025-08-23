#!/usr/bin/env python3
"""
Simple automation test for NEUROSHIELD
"""

import asyncio
import sys
from pathlib import Path

# Add app directory to path
HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parent / "app"))

async def test_basic_automation():
    """Test basic automation functionality"""
    print("=== TESTING BASIC AUTOMATION ===")
    
    try:
        from services.model_service import ModelService
        
        ms = ModelService()
        devices = ms.get_devices()
        print(f"Found devices: {devices}")
        
        if not devices:
            print("No devices found")
            return False
        
        # Test automation evaluation
        device = devices[0]
        print(f"Testing automation for {device}")
        
        result = await ms.evaluate_and_automate(device, k=10)
        print(f"Result: {result}")
        
        if result.get('ok'):
            automation_triggered = result.get('automation_triggered', [])
            print(f"Actions triggered: {automation_triggered}")
            return True
        else:
            print(f"Automation failed: {result}")
            return False
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_redis_processor():
    """Test Redis processor"""
    print("\n=== TESTING REDIS PROCESSOR ===")
    
    try:
        from services.redis_processor import redis_processor
        
        # Test queue status
        status = await redis_processor.get_queue_status()
        print(f"Queue status: {status}")
        
        # Test adding action
        test_action = {
            "device": "Router_A",
            "action_type": "test",
            "parameters": {"test": "value"},
            "priority": 1
        }
        
        success = await redis_processor.add_action(test_action)
        print(f"Action added: {success}")
        
        # Check queue again
        new_status = await redis_processor.get_queue_status()
        print(f"New queue status: {new_status}")
        
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run tests"""
    print("🚀 Simple Automation Test")
    
    test1 = await test_basic_automation()
    test2 = await test_redis_processor()
    
    print(f"\nResults: Automation={test1}, Redis={test2}")
    
    return test1 and test2

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
