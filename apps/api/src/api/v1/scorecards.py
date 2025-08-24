from fastapi import APIRouter


# Deprecated scorecards API. Kept as a no-op router to avoid 404 import errors.
router = APIRouter(prefix="/scorecards", tags=["scorecards"])


