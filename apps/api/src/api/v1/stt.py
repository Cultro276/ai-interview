from __future__ import annotations

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_session
from src.services.stt import transcribe_audio_batch
from src.core.config import settings
import asyncio
import json


router = APIRouter(prefix="/stt", tags=["stt"])


class STTRequest(BaseModel):
    interview_id: int
    audio_url: str | None = None


@router.post("/transcribe-file")
async def stt_transcribe_file(interview_id: int, file: UploadFile = File(...), session: AsyncSession = Depends(get_session)):
    try:
        data = await file.read()
        text, provider = await transcribe_audio_batch(data, file.content_type or "audio/webm")
        if not text:
            raise HTTPException(status_code=502, detail="STT provider returned empty transcript")
        # Save transcript via existing logic
        from .interviews import save_transcript, TranscriptPayload  # reuse
        payload = TranscriptPayload(text=text, provider=provider or "unknown")
        await save_transcript(interview_id, payload, session)
        return {"interview_id": interview_id, "length": len(text), "text": text}
    except HTTPException:
        # Always return 200 with empty transcript for short/silent clips
        return {"interview_id": interview_id, "length": 0, "text": ""}
    except Exception as e:
        # Do not break flow on STT failures; return empty
        return {"interview_id": interview_id, "length": 0, "text": ""}


@router.websocket("/stream/{interview_id}")
async def stt_stream(websocket: WebSocket, interview_id: int):
    """Azure Speech realtime STT bridge (Turkish).

    Client should send binary audio chunks (webm/opus recommended). We forward to Azure and
    stream partial/final transcripts back as JSON messages:
      {"type":"partial","text":"..."}
      {"type":"final","text":"..."}
    """
    await websocket.accept()
    try:
        if not (settings.azure_speech_key and settings.azure_speech_region):
            # Fallback to echo for dev if Azure not configured
            while True:
                msg = await websocket.receive_text()
                await websocket.send_text(msg)
            return
        try:
            import azure.cognitiveservices.speech as speechsdk  # type: ignore
        except Exception:
            # Library not installed → echo fallback
            while True:
                msg = await websocket.receive_text()
                await websocket.send_text(msg)
            return

        # Build Azure Speech recognizer with compressed webm/opus stream
        speech_config = speechsdk.SpeechConfig(subscription=settings.azure_speech_key, region=settings.azure_speech_region)
        speech_config.speech_recognition_language = "tr-TR"
        # Use audio classes via the speechsdk namespace to avoid submodule import issues
        stream_format = speechsdk.audio.AudioStreamFormat(
            compressed_stream_format=speechsdk.audio.AudioStreamContainerFormat.WEBM_OPUS
        )
        push_stream = speechsdk.audio.PushAudioInputStream(stream_format)
        audio_config = speechsdk.audio.AudioConfig(stream=push_stream)
        recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)

        loop = asyncio.get_running_loop()
        outbound: asyncio.Queue[str] = asyncio.Queue()

        def _q_put(payload: dict) -> None:
            try:
                asyncio.run_coroutine_threadsafe(outbound.put(json.dumps(payload)), loop)
            except Exception:
                pass

        def _on_recognizing(evt):
            if evt and getattr(evt, "result", None) and evt.result.text:
                _q_put({"type": "partial", "text": evt.result.text})

        def _on_recognized(evt):
            if evt and getattr(evt, "result", None) and evt.result.text:
                _q_put({"type": "final", "text": evt.result.text})

        recognizer.recognizing.connect(_on_recognizing)
        recognizer.recognized.connect(_on_recognized)
        recognizer.session_started.connect(lambda evt: _q_put({"type": "ready"}))
        recognizer.canceled.connect(lambda evt: _q_put({"type": "error", "reason": str(getattr(evt, "reason", "canceled"))}))

        # Start continuous recognition in a worker thread
        import threading
        def _start_rec():
            try:
                recognizer.start_continuous_recognition()
            except Exception:
                _q_put({"type": "error", "reason": "start_failed"})
        threading.Thread(target=_start_rec, daemon=True).start()

        # Consume audio from client and forward transcripts back
        async def _sender():
            try:
                while True:
                    msg = await outbound.get()
                    await websocket.send_text(msg)
            except Exception:
                return

        sender_task = asyncio.create_task(_sender())
        try:
            while True:
                message = await websocket.receive()
                if message.get("type") == "websocket.disconnect":
                    break
                data = message.get("bytes")
                if data:
                    push_stream.write(data)
                else:
                    # Ignore non-binary frames quietly
                    pass
        except WebSocketDisconnect:
            pass
        except Exception:
            pass
        finally:
            try:
                push_stream.close()
            except Exception:
                pass
            try:
                recognizer.stop_continuous_recognition()
            except Exception:
                pass
            try:
                sender_task.cancel()
            except Exception:
                pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass


