from fastapi import APIRouter

from src.core.metrics import collector


router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("")
async def get_metrics():
    return collector.snapshot()


