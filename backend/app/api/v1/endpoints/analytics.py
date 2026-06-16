from fastapi import APIRouter, HTTPException
from app.core.dependencies import get_analytics_service

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/stats")
async def get_analytics_stats():
    """Aggregated query analytics — confidence, faithfulness, mode distributions."""
    try:
        svc = get_analytics_service()
        return svc.get_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/reset")
async def reset_analytics():
    """Clear all analytics logs."""
    from app.services.analytics_service import LOG_PATH
    try:
        if LOG_PATH.exists():
            LOG_PATH.unlink()
        return {"message": "Analytics log cleared."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
