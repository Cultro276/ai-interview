from fastapi import APIRouter, Depends
from pydantic import BaseModel

from src.auth import current_active_user
from src.core.s3 import generate_presigned_put_url

router = APIRouter(prefix="/upload", tags=["upload"])


class PresignRequest(BaseModel):
    file_name: str
    content_type: str


@router.post("/presign")
async def presign(req: PresignRequest, user=Depends(current_active_user)):
    # Restrict accepted content types for security
    ct = (req.content_type or "").lower()
    allowed = {"image/", "application/pdf", "text/plain"}
    if not any(ct.startswith(p) for p in allowed):
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Unsupported content type")
    # Keep uploads prefix for generic admin uploads
    return generate_presigned_put_url(req.file_name, req.content_type, prefix="uploads")