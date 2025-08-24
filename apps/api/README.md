# AI Interview Platform - API

## Quick start

1) Requirements
- Python 3.11+
- Docker (optional)

2) Install
```
python -m venv .venv && . .venv/Scripts/activate
pip install -r requirements.txt
```

3) Environment
Create a `.env` with at least:
```
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=localhost
DB_PORT=5432
DB_NAME=interview

AWS_REGION=us-east-1
S3_BUCKET=your-bucket
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...

# LLM / Speech / TTS
GEMINI_API_KEY=...
OPENAI_API_KEY=...
AZURE_SPEECH_KEY=...
AZURE_SPEECH_REGION=westeurope
ELEVENLABS_API_KEY=...
ELEVENLABS_VOICE_ID=...

# Optional
REDIS_URL=redis://localhost:6379/0
RESEND_API_KEY=...
MAIL_FROM=no-reply@example.com
MAIL_FROM_NAME=Hirevision
```

4) Run
```
uvicorn src.main:app --reload --port 8000
```
Docs: http://localhost:8000/api/docs

## Key endpoints
- Auth: `/api/v1/auth/*`
- Jobs/Candidates/Interviews: `/api/v1/jobs`, `/api/v1/candidates`, `/api/v1/interviews`
- STT (batch): `/api/v1/stt/transcribe-file`
- STT (streaming - Azure): `/api/v1/stt/stream/{interview_id}`
  - Send binary WebM/Opus chunks; receive JSON partial/final transcripts.
- TTS (ElevenLabs default): `/api/v1/tts/speak`

## Features
- ElevenLabs TTS async with S3 caching
- Azure Speech streaming STT bridge
- S3 presigned uploads with content-type whitelists
- S3 lifecycle TTL configured at startup for media, cvs, tts
- Rate limiting with SlowAPI (Redis-backed if REDIS_URL set)

## Tests
```
pytest -q
```

## Notes
- Ensure IAM allows Get/Put/Lifecycle for S3 bucket.
- Configure `AZURE_SPEECH_KEY` / `AZURE_SPEECH_REGION` for streaming STT.
- Set `ELEVENLABS_API_KEY` / `ELEVENLABS_VOICE_ID` for TTS.
