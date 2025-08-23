#!/usr/bin/env python3
"""
Test script to include routers one by one to identify the issue
"""

from fastapi import FastAPI
import uvicorn

def test_basic_app():
    """Test basic app without routers"""
    print("🔍 Testing basic app without routers...")
    app = FastAPI()
    
    @app.get("/")
    def root():
        return {"message": "Basic app working"}
    
    print("✅ Basic app created successfully")
    return app

def test_with_predict_router():
    """Test app with predict router"""
    print("\n🔍 Testing app with predict router...")
    app = FastAPI()
    
    try:
        from app.routers import predict
        app.include_router(predict.router)
        print("✅ App with predict router created successfully")
        return app
    except Exception as e:
        print(f"❌ Failed to include predict router: {e}")
        return None

def test_with_dashboard_router():
    """Test app with dashboard router"""
    print("\n🔍 Testing app with dashboard router...")
    app = FastAPI()
    
    try:
        from app.routers import dashboard
        app.include_router(dashboard.router)
        print("✅ App with dashboard router created successfully")
        return app
    except Exception as e:
        print(f"❌ Failed to include dashboard router: {e}")
        return None

def test_with_actions_router():
    """Test app with actions router"""
    print("\n🔍 Testing app with actions router...")
    app = FastAPI()
    
    try:
        from app.routers import actions
        app.include_router(actions.router)
        print("✅ App with actions router created successfully")
        return app
    except Exception as e:
        print(f"❌ Failed to include actions router: {e}")
        return None

def test_all_routers():
    """Test app with all routers"""
    print("\n🔍 Testing app with all routers...")
    app = FastAPI()
    
    try:
        from app.routers import predict, dashboard, actions
        app.include_router(predict.router)
        app.include_router(dashboard.router)
        app.include_router(actions.router)
        print("✅ App with all routers created successfully")
        return app
    except Exception as e:
        print(f"❌ Failed to include all routers: {e}")
        return None

def main():
    """Main test function"""
    print("🚀 NEUROSHIELD Backend - Router Inclusion Test")
    print("=" * 50)
    
    # Test 1: Basic app
    app1 = test_basic_app()
    if not app1:
        return False
    
    # Test 2: With predict router
    app2 = test_with_predict_router()
    if not app2:
        print("❌ Predict router causes issue")
        return False
    
    # Test 3: With dashboard router
    app3 = test_with_dashboard_router()
    if not app3:
        print("❌ Dashboard router causes issue")
        return False
    
    # Test 4: With actions router
    app4 = test_with_actions_router()
    if not app4:
        print("❌ Actions router causes issue")
        return False
    
    # Test 5: With all routers
    app5 = test_all_routers()
    if not app5:
        print("❌ All routers together cause issue")
        return False
    
    print("\n🎉 All router tests passed!")
    print("The issue is not with router inclusion.")
    return True

if __name__ == "__main__":
    success = main()
    if success:
        print("\n✅ All tests passed. The issue is elsewhere.")
    else:
        print("\n❌ Found the issue with router inclusion.")

