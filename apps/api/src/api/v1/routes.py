from fastapi import APIRouter
from .jobs import router as jobs_router
from .auth import router as auth_router
from .candidates import router as candidates_router
from .interviews import router as interviews_router
from .interviews import candidate_router as interviews_candidate_router
from .conversations import router as conversations_router
from .conversations import public_router as conversations_public_router
from .upload import router as upload_router
from .tokens import router as tokens_router
from .conversation import router as convo_router
from .metrics import router as metrics_router
from .tts import router as tts_router
from .stt import router as stt_router

router = APIRouter(tags=["utils"])


@router.get("/echo")
async def echo(msg: str = "hello"):
    """Return back whatever message was sent."""
    return {"message": msg}

router.include_router(jobs_router)
router.include_router(auth_router)
router.include_router(candidates_router)
router.include_router(interviews_router)
router.include_router(interviews_candidate_router)
router.include_router(conversations_router)
router.include_router(conversations_public_router)
router.include_router(upload_router)
router.include_router(tokens_router)
router.include_router(convo_router) 
router.include_router(metrics_router)
router.include_router(tts_router)
router.include_router(stt_router)