# backend/app/routers/predict.py
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
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
