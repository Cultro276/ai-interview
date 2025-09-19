## Interview Flow and Realtime Behaviors

This document summarizes the server and client flow for the voice interview experience, including realtime/WebRTC mode, SSE streaming mode, barge‑in, pause/resume, VAD ducking, memory usage, and completion logic.

### High-level flow
- Candidate opens `apps/web/app/interview/[token]/page.tsx` via a unique `token`.
- Steps: consent → permissions → device test → intro → interview.
- On entering interview:
  - Client prepares WebAudio graph, MediaRecorders, and state (phase: idle/speaking/listening/thinking).
  - If `NEXT_PUBLIC_INTERVIEW_REALTIME` is true: the client requests an ephemeral OpenAI Realtime session from `/api/v1/realtime/ephemeral` and connects via WebRTC; the model will speak the question.
  - Else (legacy TTS flow): the client fetches/generates the question, plays TTS, then listens and transcribes.

### Generating questions (API)
- `POST /api/v1/interview/next-question` (`apps/api/src/api/v1/interview_flow.py`):
  - Loads interview, job, candidate, and optional parsed resume text.
  - First question path: hidden LLM context (job, resume, company, recruiter extra questions, scenarios) → `generate_question_robust` with Gemini and fallbacks. Emergency fallbacks if providers fail. Intro greeting is added, deduplicating greetings. The question is persisted via `persist_assistant_message` and session memory is updated.
  - Follow‑up path: builds `combined_ctx` using job description, recruiter extra questions, session memory snapshot via `build_memory_section`, optional analysis blobs (requirements plan and coverage), behavior `signals`, and short‑answer hints. Then delegates to provider‑agnostic orchestrator `src/services/llm_orchestrator.py` (OpenAI→Gemini→local fallback). Output is sanitized, optionally polished, de‑genericized, and re‑biased to pending recruiter questions.
  - FINISHED flag: if `FINISHED` detected (after sanitization), returns `done=True`.
  - Salary completion: if a salary question has been asked and answered and at least 5 assistant turns occurred, returns `done=True`.

- `POST /api/v1/interview/next-turn`:
  - Validates token, optional on‑server STT for uploaded audio (`audio_b64`) via `transcribe_audio_batch`.
  - Content safety analysis (non‑blocking), persists user turn with idempotency.
  - Rebuilds full DB history, enriches in‑memory session memory, computes live analysis/score (for recruiter UI) and may early‑stop based on evidence thresholds from `src/core/config.py`.
  - Optional adaptive questioning path (`src/services/adaptive_questions`) can produce a targeted question directly.
  - Otherwise calls `next_question` and persists the assistant turn (safety‑validated).

### Streaming (SSE) mode
- Client calls `GET /api/v1/realtime/interview/stream?interview_id=...&token=...&text=...` when `NEXT_PUBLIC_INTERVIEW_STREAMING` is true.
- Server builds a strong system persona using `RECRUITER_PERSONA` and `build_role_guidance_block(job_desc)` and streams tokens from OpenAI Chat Completions API.
- SSE events:
  - `ready`: stream initialized (also published to Redis fanout).
  - `delta`: partial token chunks; also published to fanout.
  - `done`: final text length; also published to fanout. Assistant message is persisted once complete.
- Subscriber endpoint: `GET /api/v1/realtime/interview/subscribe?interview_id=...` relays events from Redis fanout (`src/services/fanout.py`).

### Realtime (WebRTC) mode
- `POST /api/v1/realtime/ephemeral` creates an OpenAI Realtime session with contextual `instructions` (company, role) and returns the server response, saving it to a 120‑second ephemeral store. Client uses `client_secret.value` for WebRTC SDP exchange.
- Client logic in `apps/web/lib/realtime.ts`:
  - `getEphemeralToken(interviewId, model, voice)` fetches the ephemeral session from the API.
  - `connectWebRTC(ephemeralKey)` sets up `RTCPeerConnection`, attaches microphone tracks, opens a data channel `oai-events`, and completes SDP exchange against OpenAI Realtime endpoint. Returns `{ pc, audioEl, dc }`.
- The model speaks directly to the browser audio element. The client does not play TTS in realtime mode.

### VAD, barge‑in, pause/resume, ducking (Client)
- Implemented in `apps/web/app/interview/[token]/page.tsx`:
  - WebAudio graph: mic path → compressor → gain → analyser; optional TTS path via `ttsGain` into `MediaStreamDestination` to mix mic + TTS for recordings.
  - VAD loop uses `AnalyserNode` RMS calculation to detect `speakingLikely`.
  - Ducking: while candidate speaks, `ttsGain.gain` is eased toward ~0.25; otherwise toward ~0.85.
  - Barge‑in: if `speakingLikely` while phase is `speaking`, stop current TTS and send `{type: "response.cancel"}` over the Realtime data channel when open. Then switch to `listening`.
  - Pause/Resume: UI button toggles `paused`. On pause, stops TTS and sends `{type: "response.cancel"}` if realtime channel open; sets phase to `idle`. On resume (non‑realtime), re‑speaks the current question via TTS and flips to `listening`.

### STT and fallbacks (Client → Server)
- Primary path (legacy TTS mode):
  - Browser speech capture via `listen(...)` builds a transcript buffer with adaptive silence detection; if too short, server Whisper fallback is used.
  - Per‑answer audio is recorded separately (audio‑only MediaRecorder) to upload for server STT when needed (`/api/v1/stt/transcribe-file?interview_id=...`).
- Server STT entry points:
  - `transcribe_audio_batch(audio_bytes, "audio/webm")` within `next-turn` when `audio_b64` provided.
  - File upload in UI triggers `/stt/transcribe-file` which returns `{ text }` for Whisper/Azure depending on config.

### Session memory
- In‑memory `src/services/memory_store.py` tracks rolling summary and last N turns.
- `build_memory_section` converts snapshot into a hidden guidance block to steer the LLM without leaking PII.
- `enrich_session_memory` updates the store using DB conversation history each turn.

### Content safety and sanitization
- User input analyzed via `src/services/content_safety.analyze_input` (non‑blocking).
- Assistant output validated with `validate_assistant_question` and sanitized with `sanitize_question_text` (filters links/PII, FINISHED flag handling).

### Completion heuristics
- Done if: FINISHED flag detected, or salary question asked and answered after ≥5 assistant turns.
- Evidence‑based early finish inside `next-turn`: if requirements coverage meets configured thresholds (`src/core/config.py`) for strong/negative/mixed outcomes.

### Redis fanout and ephemeral store
- Redis fanout in `src/services/fanout.py`: `_channel_for_interview(id)` + `publish_event` + `subscribe_events`. Used by SSE producer to broadcast `ready`, `delta`, `done`.
- Ephemeral store in `src/services/ephemeral_store.py`: stores OpenAI session payloads for 120s with generated `_ephemeral_id`.

### Environment flags
- `NEXT_PUBLIC_INTERVIEW_REALTIME`: enable WebRTC OpenAI Realtime.
- `NEXT_PUBLIC_INTERVIEW_STREAMING`: enable SSE token streaming path.
- `NEXT_PUBLIC_TTS_PROVIDER`: select TTS provider for legacy mode.
- `NEXT_PUBLIC_FORCE_WHISPER`: force server‑side Whisper fallback on each answer.

### Key files
- Server:
  - `apps/api/src/api/v1/interview_flow.py`
  - `apps/api/src/api/v1/realtime.py`
  - `apps/api/src/services/llm_orchestrator.py`
  - `apps/api/src/services/context_builder.py`
  - `apps/api/src/services/content_safety.py`
  - `apps/api/src/services/fanout.py`
  - `apps/api/src/services/ephemeral_store.py`
- Client:
  - `apps/web/app/interview/[token]/page.tsx`
  - `apps/web/lib/realtime.ts`


