from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.v1.routes import router as api_v1_router
from src.core.metrics import collector

app = FastAPI(
    title="Interview API",
    version="1.0.0",
    openapi_url="/api/openapi.json",
    docs_url="/api/docs",
)

# CORS – local dev origins
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost",
    "http://127.0.0.1",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/healthz", tags=["health"])
def healthcheck():
    return {"status": "ok", **collector.snapshot()}


# Dev-only stub endpoint for fake uploads when S3 is not configured
@app.put("/dev-upload/{path:path}", tags=["dev"], include_in_schema=False)
def dev_upload_stub(path: str):
    # Accept payload and return 200 to simulate S3 upload success
    return JSONResponse({"ok": True, "path": path})


# Versioned API
app.include_router(api_v1_router, prefix="/api/v1") 