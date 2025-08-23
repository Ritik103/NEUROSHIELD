# backend/app/routers/predict.py
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from datetime import datetime
from app.services.model_service import ModelService

router = APIRouter()
svc = ModelService()

@router.get("/api/predict/device/{device}")
def predict_device(device: str, k: int = Query(120, description="Number of latest rows to use")):
    try:
        res = svc.predict_for_device(device, k=k)
        if not res.get("ok", False):
            raise HTTPException(status_code=400, detail=res.get("reason") or res.get("error"))
        return res
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/predict/all")
def predict_all(k: int = Query(120, description="Number of latest rows per device to use")):
    try:
        results = svc.predict_all_devices(k=k)
        return {"devices": results}
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/predict/automated")
async def predict_with_automation(k: int = Query(120, description="Number of recent data points to use")):
    """Get predictions with automation evaluation for all devices"""
    try:
        predictions = await svc.evaluate_all_devices_with_automation(k=k)
        return {
            "predictions": predictions,
            "total_devices": len(predictions),
            "automation_enabled": True,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting automated predictions: {str(e)}")

@router.get("/api/predict/device/{device}/automated")
async def predict_device_with_automation(device: str, k: int = Query(120, description="Number of recent data points to use")):
    """Get prediction with automation evaluation for a specific device"""
    try:
        prediction = await svc.evaluate_and_automate(device, k=k)
        return {
            "prediction": prediction,
            "device": device,
            "automation_enabled": True,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting automated prediction: {str(e)}")
