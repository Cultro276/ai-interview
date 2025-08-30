"use client";
import { useEffect, useState, useRef, useMemo } from "react";
import { apiFetch } from "@/lib/api";
import { listen } from "@/lib/voice";
import { Steps } from "@/components/ui/Steps";
import { Button } from "@/components/ui/Button";

export default function InterviewPage({ params }: { params: { token: string } }) {
  const { token } = params;
  const forceWhisper = typeof window !== "undefined" && process.env.NEXT_PUBLIC_FORCE_WHISPER === "true";
  const [status, setStatus] = useState<
    | "loading"
    | "invalid"
    | "consent"
    | "permissions"
    | "permissionsDenied"
    | "test"
    | "intro"
    | "interview"
    | "finished"
  >("loading");
  const [error, setError] = useState<string | null>(null);
  const [accepted, setAccepted] = useState(false);
  const [permissionError, setPermissionError] = useState<string | null>(null);
  const [camPerm, setCamPerm] = useState<string | null>(null);
  const [micPerm, setMicPerm] = useState<string | null>(null);
  const [stream, setStream] = useState<MediaStream | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioRecorderRef = useRef<MediaRecorder | null>(null);
  const videoChunksRef = useRef<Blob[]>([]);
  const audioChunksRef = useRef<Blob[]>([]);
  const recStartTimeRef = useRef<number>(0);
  // intro confirmation checkbox
  const [ready, setReady] = useState(false);
  const [devicesOk, setDevicesOk] = useState(false);

  // Conversational states
  const [question, setQuestion] = useState<string | null>(null);
  const [phase, setPhase] = useState<"idle" | "speaking" | "listening" | "thinking">("idle");
  const [history, setHistory] = useState<{ role: "assistant" | "user"; text: string }[]>([]);
  const askedCount = useMemo(() => history.filter(t => t.role === "assistant").length, [history]);
  const [elapsedSec, setElapsedSec] = useState(0);
  // Accessibility toggles
  const [showCaptions, setShowCaptions] = useState(true);
  
  // Conversation tracking
  const [interviewId, setInterviewId] = useState<number | null>(null);
  const [interviewJobId, setInterviewJobId] = useState<number | null>(null);
  const preparedFirstQuestionRef = useRef<string | null>(null);
  const firstQuestionIssuedRef = useRef<boolean>(false);
  const sequenceNumberRef = useRef<number>(0);
  const audioStartIndexRef = useRef<number>(0);
  // Dedicated per-answer audio recorder to produce a single valid container
  const answerRecorderRef = useRef<MediaRecorder | null>(null);
  const answerChunksRef = useRef<Blob[]>([]);

  const videoRef = useRef<HTMLVideoElement>(null);
  // WebAudio for mixing mic + TTS
  const audioCtxRef = useRef<AudioContext | null>(null);
  const mixDestRef = useRef<MediaStreamAudioDestinationNode | null>(null);
  const micGainRef = useRef<GainNode | null>(null);
  const ttsGainRef = useRef<GainNode | null>(null);
  const currentTtsSourceRef = useRef<AudioBufferSourceNode | null>(null);
  // Block public message posts after completion to avoid 400s
  const canPostPublicRef = useRef<boolean>(true);

  const playTTS = async (text: string, onEnded?: () => void) => {
    try {
      if (!audioCtxRef.current) return onEnded?.();
      if (audioCtxRef.current.state === "suspended") {
        try { await audioCtxRef.current.resume(); } catch {}
      }
      const base = (process.env.NEXT_PUBLIC_API_URL || `${window.location.protocol}//${window.location.hostname}:8000`).replace(/\/+$/g, "");
      const res = await fetch(`${base}/api/v1/tts/speak`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "Accept": "audio/mpeg" },
        body: JSON.stringify({ text, lang: "tr", provider: process.env.NEXT_PUBLIC_TTS_PROVIDER || undefined }),
      });
      if (!res.ok) throw new Error(`TTS failed: ${res.status}`);
      const buf = await res.arrayBuffer();
      const audioBuffer = await audioCtxRef.current.decodeAudioData(buf);
      const src = audioCtxRef.current.createBufferSource();
      src.buffer = audioBuffer;
      // If mixing available, route to ttsGain; otherwise to speakers so candidate hears it
      if (ttsGainRef.current) {
        src.connect(ttsGainRef.current);
        // Also route to speakers so candidate hears AI voice while it's mixed into the recording
        src.connect(audioCtxRef.current.destination);
      } else {
        src.connect(audioCtxRef.current.destination);
      }
      src.onended = () => onEnded?.();
      currentTtsSourceRef.current = src;
      src.start(0);
    } catch (e) {
      console.error("TTS error", e);
      onEnded?.();
    }
  };

  // Save conversation message to database (no-redirect for unauthenticated candidate)
  const saveConversationMessage = async (role: "assistant" | "user" | "system", content: string) => {
    if (!interviewId || !canPostPublicRef.current) return;
    try {
      sequenceNumberRef.current += 1;
      const base = (process.env.NEXT_PUBLIC_API_URL || `${window.location.protocol}//${window.location.hostname}:8000`).replace(/\/+$/g, "");
      await fetch(`${base}/api/v1/conversations/messages-public`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          interview_id: interviewId,
          role,
          content,
          sequence_number: sequenceNumberRef.current,
          token,
        }),
      });
    } catch (error) {
      // best-effort only in candidate UI
    }
  };

  // Get or create interview record and save initial system message
  const initializeInterview = async () => {
    try {
      // Fetch existing interview for this candidate by token (created by admin flow)
      const interview = await apiFetch<{ id: number; job_id: number; prepared_first_question?: string | null }>(`/api/v1/interviews/by-token/${token}`);
      setInterviewId(interview.id);
      setInterviewJobId(interview.job_id);
      preparedFirstQuestionRef.current = (interview as any).prepared_first_question || null;
      sequenceNumberRef.current = 0;
      // Save system message to indicate interview started
      const systemMessage = `Interview started at ${new Date().toISOString()}`;
      const base = (process.env.NEXT_PUBLIC_API_URL || `${window.location.protocol}//${window.location.hostname}:8000`).replace(/\/+$/g, "");
      await fetch(`${base}/api/v1/conversations/messages-public`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          interview_id: interview.id,
          role: "system",
          content: systemMessage,
          sequence_number: 0,
          token,
        }),
      });
    } catch (error) {
      console.error("Failed to initialize interview:", error);
    }
  };

  // Verify the token once on mount
  useEffect(() => {
    apiFetch(`/api/v1/tokens/verify?token=${token}`, { method: "POST" })
      .then(() => {
        setStatus("consent");
        initializeInterview();
      })
      .catch((err: Error) => {
        setError(err.message);
        setStatus("invalid");
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // When we enter the permissions step, request camera/mic access
  useEffect(() => {
    if (status !== "permissions") return;

    navigator.mediaDevices
      .getUserMedia({ video: true, audio: true })
      .then((s) => {
        setStream(s);
        setStatus("test");
      })
      .catch((err) => {
        console.error("Permission error", err);
        setPermissionError(err.message);
        setStatus("permissionsDenied");
      });
  }, [status]);

  // Attach stream to video element when ready (test/intro/interview)
  useEffect(() => {
    if (videoRef.current && stream && ["test", "intro", "interview"].includes(status)) {
      (videoRef.current as any).srcObject = stream;
    }
  }, [status, stream]);

  // Note: upload handled in the unified effect below

  // Query permission states once we reach test step
  useEffect(() => {
    if (status !== "test" || !navigator.permissions) return;
    navigator.permissions.query({ name: "camera" as PermissionName }).then((p) => setCamPerm(p.state));
    navigator.permissions.query({ name: "microphone" as PermissionName }).then((p) => setMicPerm(p.state));
  }, [status]);

  const sanitizeQuestion = (q: string) => (q || "").replace(/\bFINISHED\b/gi, "").trim();

  // Schedule first question: use prepared question if available; otherwise fetch
  useEffect(() => {
    if (status !== "interview" || question !== null || firstQuestionIssuedRef.current) return;
    const id = setTimeout(async () => {
      if (firstQuestionIssuedRef.current) return;
      const prepared = preparedFirstQuestionRef.current;
      if (prepared && prepared.trim()) {
        const q = sanitizeQuestion(prepared.trim());
        if (!q) {
          // If prepared is effectively FINISHED/empty, end early
          setStatus("finished");
          setPhase("idle");
          return;
        }
        setQuestion(q);
        setHistory((h) => [...h, { role: "assistant", text: q }]);
        setPhase("speaking");
        firstQuestionIssuedRef.current = true;
        return;
      }
      // Fallback to API-generated first question
      const initialHistory: { role: "assistant" | "user"; text: string }[] = [];
      apiFetch<{ question: string | null; done: boolean }>("/api/v1/interview/next-question", {
        method: "POST",
        body: JSON.stringify({ history: initialHistory, interview_id: interviewId }),
      })
        .then((res) => {
          let firstQuestion = sanitizeQuestion(res.question || "");
          if (!firstQuestion) {
            if (res.done) {
              setStatus("finished");
              setPhase("idle");
              firstQuestionIssuedRef.current = true;
              return;
            }
            firstQuestion = "Merhaba, kendinizi tanıtır mısınız?";
          }
          setQuestion(firstQuestion);
          setHistory((h) => [...h, { role: "assistant", text: firstQuestion }]);
          setPhase("speaking");
          firstQuestionIssuedRef.current = true;
        })
        .catch(() => {
          const firstQuestion = "Merhaba, kendinizi tanıtır mısınız?";
          setQuestion(firstQuestion);
          setHistory((h) => [...h, { role: "assistant", text: firstQuestion }]);
          setPhase("speaking");
          firstQuestionIssuedRef.current = true;
        });
    }, 1500);
    return () => clearTimeout(id);
  }, [status, question, interviewId]);

  // Speak current question and then listen for answer
  useEffect(() => {
    if (status !== "interview" || question === null) return;

    let rec: any = null;

    // Anti-cheat: tab visibility / focus loss events (best-effort)
    const sendSignal = async (kind: string, meta?: string) => {
      try {
        const base = (process.env.NEXT_PUBLIC_API_URL || `${window.location.protocol}//${window.location.hostname}:8000`).replace(/\/+$/g, "");
        await fetch(`${base}/api/v1/signals/public`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ token, interview_id: interviewId, kind, meta }),
        });
      } catch {}
    };
    const handleVisibilityChange = () => {
      if (document.hidden) {
        sendSignal("tab_hidden");
      }
    };
    const handleWindowBlur = () => {
      sendSignal("focus_lost");
    };

    // Force ElevenLabs when available by adding provider in query body
    playTTS(question, () => {
      setPhase("listening");
      // mark the start index for recent audio chunks to enable Whisper fallback STT per answer
      try { audioStartIndexRef.current = audioChunksRef.current.length; } catch {}
      // Start a dedicated per-answer audio recorder to ensure a single self-contained blob
      try {
        const audioOnlyStream = mixDestRef.current && mixDestRef.current.stream.getAudioTracks().length
          ? mixDestRef.current.stream
          : (stream ? new MediaStream(stream.getAudioTracks()) : null);
        if (audioOnlyStream && audioOnlyStream.getAudioTracks().length) {
          answerChunksRef.current = [];
          const mimeCandidates = [
            "audio/webm",
            "audio/ogg;codecs=opus",
            "audio/mp4",
          ];
          // Prefer OGG/Opus for Azure STT compatibility; fallback to webm/mp4
          const chosen = (window as any).MediaRecorder && typeof (window as any).MediaRecorder.isTypeSupported === "function"
            ? (mimeCandidates.find((t) => t.startsWith("audio/ogg") && (window as any).MediaRecorder.isTypeSupported(t))
              || mimeCandidates.find((t) => (window as any).MediaRecorder.isTypeSupported(t))
              || undefined)
            : undefined;
          const ansRec = new MediaRecorder(audioOnlyStream, chosen ? { mimeType: chosen } : undefined);
          ansRec.ondataavailable = (e) => { answerChunksRef.current.push(e.data); };
          // Start without timeslice to get a single final Blob upon stop
          ansRec.start();
          answerRecorderRef.current = ansRec;
        }
      } catch {}

      let buffer: string[] = [];
      let silenceTimer: any = null;
      let hardStopTimer: any = null;
      let finalized = false;

      const finalize = async () => {
        if (finalized) return;
        finalized = true;
        if (rec && rec.stop) rec.stop();
        // Stop per-answer recorder to finalize a single blob
        if (answerRecorderRef.current && answerRecorderRef.current.state !== "inactive") {
          try { (answerRecorderRef.current as any).requestData?.(); } catch {}
          answerRecorderRef.current.stop();
          await new Promise(resolve => {
            answerRecorderRef.current!.addEventListener("stop", resolve, { once: true });
          });
        }
        if (silenceTimer) clearTimeout(silenceTimer);
        if (hardStopTimer) clearTimeout(hardStopTimer);
        let full = buffer.join(" ").trim();
        if (forceWhisper) {
          full = ""; // always force server-side Whisper
        }
        // If browser STT is empty or too short, try Whisper on recent mixed audio
        if (!full || full.length < 10) {
          try {
            // Prefer the dedicated per-answer recording if available
            const hasAnswerBlob = answerChunksRef.current.length > 0;
            if (hasAnswerBlob) {
              const type = answerChunksRef.current[0]?.type || "audio/webm";
              const clip = new Blob(answerChunksRef.current, { type });
              const fd = new FormData();
              const ext = type.includes("mp4") ? "mp4" : type.includes("ogg") ? "ogg" : type.includes("webm") ? "webm" : type.includes("wav") ? "wav" : "bin";
              fd.append("file", clip, `answer.${ext}`);
              const base = (process.env.NEXT_PUBLIC_API_URL || `${window.location.protocol}//${window.location.hostname}:8000`).replace(/\/+$/g, "");
              const resp = await fetch(`${base}/api/v1/stt/transcribe-file?interview_id=${interviewId}`, { method: "POST", body: fd });
              if (resp.ok) {
                const data = await resp.json();
                const whisperText = (data?.text || "").trim();
                if (whisperText) {
                  full = whisperText;
                }
              }
            }
          } catch {}
          if (!full) {
            // Last resort fallback to avoid getting stuck
            full = "...";
          }
        }

        // Update history with user's answer
        const newHistoryLocal: { role: "assistant" | "user"; text: string }[] = [...history, { role: "user", text: full }];
        setHistory(newHistoryLocal);
        setPhase("thinking");

        // Save user's answer to database
        saveConversationMessage("user", full);

        // Behavior signals for adaptive tone
        const signals: string[] = [];
        try {
          if (buffer.join(" ").trim().length < 10) signals.push("very_short_answer");
        } catch {}
        apiFetch<{ question: string | null; done: boolean }>(
          "/api/v1/interview/next-question",
          {
            method: "POST",
            body: JSON.stringify({ history: newHistoryLocal, interview_id: interviewId, signals }),
          },
        )
          .then((res) => {
            if (res.done) {
              setPhase("idle");
              setStatus("finished");
              // Save completion message
              saveConversationMessage("system", "Interview completed");
            } else {
              let nextQ = sanitizeQuestion(res.question || "");
              if (!nextQ) {
                // Treat empty/FINISHED-only responses as completion
                setPhase("idle");
                setStatus("finished");
                saveConversationMessage("system", "Interview completed");
                return;
              }
              // Avoid duplicate consecutive questions
              setHistory((h) => {
                const last = h[h.length - 1];
                if (last && last.role === "assistant" && last.text.trim() === nextQ) {
                  return h;
                }
                setQuestion(nextQ);
                setPhase("speaking");
                return [...h, { role: "assistant", text: nextQ }];
              });
            }
          })
          .catch((err) => {
            console.error("AI error", err);
            const errorMessage = "Maalesef bir hata oluştu. Lütfen daha sonra yeniden deneyin.";
            setQuestion(errorMessage);
            setPhase("speaking");
            // Save error message
            saveConversationMessage("system", `Error occurred: ${err.message}`);
          });
      };

      const listenStart = Date.now();

      document.addEventListener("visibilitychange", handleVisibilityChange);
      window.addEventListener("blur", handleWindowBlur);
      rec = listen(
        (t) => {
          // Ignore very short/placeholder transcripts
          const clean = (t || "").trim();
          if (!clean || clean === "..." || clean.length < 2) return;
          buffer.push(clean);
          // Each time we get speech, reset timer; hold a bit longer to avoid early cutoff
          if (silenceTimer) clearTimeout(silenceTimer);
          const minHold = Math.max(0, 2200 - (Date.now() - listenStart));
          silenceTimer = setTimeout(finalize, 3400 + minHold);
        },
        () => {
          // Only finalize if we have some content; otherwise keep listening for a short grace period
          if (buffer.length > 0) finalize();
        }
      );

      // Safety net: allow longer answers but still fail-safe
      hardStopTimer = setTimeout(() => { if (buffer.length > 0) finalize(); }, 14000);
    });

    return () => {
      if (rec && rec.stop) rec.stop();
      try { currentTtsSourceRef.current?.stop(0); } catch {}
      try { document.removeEventListener("visibilitychange", handleVisibilityChange); } catch (e) {}
      try { window.removeEventListener("blur", handleWindowBlur); } catch (e) {}
      // Clean up timers if needed
      if (typeof (window as any).silenceTimer !== "undefined" && (window as any).silenceTimer) clearTimeout((window as any).silenceTimer);
      if (typeof (window as any).hardStopTimer !== "undefined" && (window as any).hardStopTimer) clearTimeout((window as any).hardStopTimer);
    };
  }, [status, question]);

  // Lightweight timer (no user interaction)
  useEffect(() => {
    if (status !== "interview") return;
    const id = setInterval(() => setElapsedSec((s)=>s+1), 1000);
    return () => clearInterval(id);
  }, [status]);

  // --- Start recording when interview begins ---
  // 1) Video+Audio recorder with codec fallback and timeslice chunks
  useEffect(() => {
    if (status !== "interview" || !stream) return;
    try {
      console.log("Starting recording with stream tracks:", stream.getTracks().length);
      // Prefer a supported mimeType for video
      const videoMimeCandidates = [
        // Prefer VP8 for broadest compatibility across Chromium-based browsers
        "video/webm;codecs=vp8,opus",
        "video/webm;codecs=vp9,opus",
        "video/webm",
      ];
      const chosenVideoMime = (window as any).MediaRecorder && typeof (window as any).MediaRecorder.isTypeSupported === "function"
        ? videoMimeCandidates.find((t) => (window as any).MediaRecorder.isTypeSupported(t)) || undefined
        : undefined;
      // Reset chunk buffers before starting
      videoChunksRef.current = [];
      audioChunksRef.current = [];
      // Build WebAudio mixing graph (mic + tts)
      const audioCtx = new (window.AudioContext || (window as any).webkitAudioContext)();
      audioCtxRef.current = audioCtx;
      // Prefer createMediaStreamDestination; gracefully degrade if unavailable
      let dest: MediaStreamAudioDestinationNode | null = null;
      if (typeof (audioCtx as any).createMediaStreamDestination === "function") {
        dest = (audioCtx as any).createMediaStreamDestination();
      }
      mixDestRef.current = dest;
      // Mic pipeline
      const micSource = audioCtx.createMediaStreamSource(stream);
      const micGain = audioCtx.createGain();
      micGain.gain.value = 1.0;
      micGainRef.current = micGain;
      if (dest) {
        micSource.connect(micGain).connect(dest);
      }
      // TTS pipeline (only if mixing available)
      if (dest) {
        const ttsGain = audioCtx.createGain();
        ttsGain.gain.value = 0.9;
        ttsGainRef.current = ttsGain;
        ttsGain.connect(dest);
      } else {
        ttsGainRef.current = null;
      }

      // Combine video track with mixed audio if available; otherwise fallback to original stream
      const combinedStream = dest && dest.stream.getAudioTracks().length
        ? new MediaStream([...stream.getVideoTracks(), ...dest.stream.getAudioTracks()])
        : stream;
      const rec = new MediaRecorder(combinedStream, chosenVideoMime ? { mimeType: chosenVideoMime } : undefined);
      rec.ondataavailable = (e) => {
        // accumulate chunks silently
        videoChunksRef.current.push(e.data);
      };
      // Start with a small timeslice to ensure regular dataavailable events across browsers
      rec.start(1000);
      mediaRecorderRef.current = rec;

      // 2) Audio-only recorder from mixed destination, fallback to mic-only
      const audioOnlyStream = mixDestRef.current && mixDestRef.current.stream.getAudioTracks().length
        ? mixDestRef.current.stream
        : new MediaStream(stream.getAudioTracks());
      if (audioOnlyStream.getAudioTracks().length) {
        const audioMimeCandidates = [
          "audio/mp4",              // ← En uyumlu format önce
          "audio/webm",             // ← Codec olmadan WebM
          "audio/ogg;codecs=opus",
          "audio/webm;codecs=opus", // ← Sorunlu codec en sona
        ];
        const chosenAudioMime = (window as any).MediaRecorder && typeof (window as any).MediaRecorder.isTypeSupported === "function"
          ? audioMimeCandidates.find((t) => (window as any).MediaRecorder.isTypeSupported(t)) || undefined
          : undefined;
        const audioRec = new MediaRecorder(audioOnlyStream, chosenAudioMime ? { mimeType: chosenAudioMime } : undefined);
        audioRec.ondataavailable = (e) => {
          // accumulate chunks silently
          audioChunksRef.current.push(e.data);
        };
        // Start with timeslice to flush data regularly
        audioRec.start(1000);
        audioRecorderRef.current = audioRec;
      }
    } catch (e) {
      console.error("MediaRecorder error:", e);
    }
  }, [status, stream]);

  // Upload media when interview finishes (must be declared before any early returns)
  useEffect(() => {
    if (status !== "finished") return;
    const uploadMedia = async () => {
      try {
        console.log("Starting media upload...");
        // Stop sending public messages – token will be marked used
        canPostPublicRef.current = false;

        // Stop recorders and get final data (force flush last chunk)
        if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
          try { (mediaRecorderRef.current as any).requestData?.(); } catch {}
          mediaRecorderRef.current.stop();
          await new Promise(resolve => {
            mediaRecorderRef.current!.addEventListener("stop", resolve, { once: true });
          });
        }

        if (audioRecorderRef.current && audioRecorderRef.current.state !== "inactive") {
          try { (audioRecorderRef.current as any).requestData?.(); } catch {}
          audioRecorderRef.current.stop();
          await new Promise(resolve => {
            audioRecorderRef.current!.addEventListener("stop", resolve, { once: true });
          });
        }

        // Create blobs from chunks (infer type from first chunk if present)
        const videoType = videoChunksRef.current[0]?.type || "video/webm";
        const audioType = audioChunksRef.current[0]?.type || "audio/webm";
        const videoBlob = new Blob(videoChunksRef.current, { type: videoType });
        const audioBlob = new Blob(audioChunksRef.current, { type: audioType });

        console.log("Video blob size:", videoBlob.size, "Audio blob size:", audioBlob.size);

        // Helper: presign
        const presign = async (kind: "video" | "audio", type: string) => {
          const name = `interview-${token}-${kind}-${Date.now()}.webm`;
          return apiFetch<{ presigned_url: string }>("/api/v1/tokens/presign-upload", {
            method: "POST",
            body: JSON.stringify({ token, file_name: name, content_type: type }),
          });
        };
        // Helper: PUT with 1 retry (new presign on failure)
        const putWithRetry = async (
          kind: "video" | "audio",
          blob: Blob,
          type: string,
        ) => {
          if (blob.size === 0) return { ok: false, url: null } as const;
          try {
            const p1 = await presign(kind, type);
            const r1 = await fetch(p1.presigned_url, { method: "PUT", body: blob, headers: { "Content-Type": type } });
            if (r1.ok) return { ok: true, url: p1.presigned_url.split("?")[0] } as const;
          } catch {}
          try {
            const p2 = await presign(kind, type);
            const r2 = await fetch(p2.presigned_url, { method: "PUT", body: blob, headers: { "Content-Type": type } });
            if (r2.ok) return { ok: true, url: p2.presigned_url.split("?")[0] } as const;
          } catch {}
          return { ok: false, url: null } as const;
        };

        const [videoRes, audioRes] = await Promise.all([
          putWithRetry("video", videoBlob, videoType),
          putWithRetry("audio", audioBlob, audioType),
        ]);
        console.log("upload video ok=", videoRes.ok, "audio ok=", audioRes.ok);

        // Save media URLs to interview record and get interview ID
        const videoUrl = videoRes.ok ? (videoRes.url as string) : null;
        const audioUrl = audioRes.ok ? (audioRes.url as string) : null;
        const interviewRecord = await apiFetch<{ id: number }>(`/api/v1/interviews/${token}/media`, {
          method: "PATCH",
          body: JSON.stringify({ video_url: videoUrl, audio_url: audioUrl })
        });
        setInterviewId(interviewRecord.id);
        console.log("Interview ID captured:", interviewRecord.id);
        // Do not send further public messages after media upload, since the server marks
        // the candidate token as used at this point and will reject new messages (400).
      } catch (error) {
        console.error("Media upload failed:", error);
      }
    };
    uploadMedia();
  }, [status, token]);

  if (status === "loading") return <p>Doğrulanıyor…</p>;
  if (status === "invalid") return <p>{error || "Bağlantı geçersiz veya süresi dolmuş."}</p>;

  if (status === "consent") {
    return (
      <div className="max-w-xl mx-auto p-6">
        <Steps steps={["Aydınlatma", "İzinler", "Cihaz Testi", "Tanıtım", "Mülakat"]} current={0} className="mb-6" />
        <h1 className="text-2xl font-semibold mb-2">KVKK Aydınlatma Metni</h1>
        <p className="text-gray-700">
          Bu video mülâkat sırasında kaydedilen görüntü ve ses verileriniz, işe alım sürecinin yürütülmesi amacıyla işlenecek ve saklanacaktır.
        </p>
        <p className="text-sm mt-2">
          Tam metni okumak için <a href="/privacy" target="_blank" rel="noreferrer" className="text-brand-700 underline">KVKK / Gizlilik Metni</a>
        </p>
        <label className="block my-4">
          <input
            type="checkbox"
            className="mr-2"
            checked={accepted}
            onChange={(e) => setAccepted(e.target.checked)}
          />
          KVKK metnini okudum ve kabul ediyorum.
        </label>
        <Button
          disabled={!accepted}
          onClick={async () => {
            try {
              // Persist consent before moving to permissions
              await apiFetch(`/api/v1/tokens/consent`, {
                method: "POST",
                body: JSON.stringify({ token, interview_id: interviewId, text_version: "v1" }),
              });
            } catch (e) {
              // best-effort; do not block candidate flow
              console.warn("consent failed", e);
            }
            setStatus("permissions");
          }}
        >Devam Et</Button>
      </div>
    );
  }

  // permissions step placeholder – will handle camera/mic permissions next
  if (status === "permissions") return <p>Kamera ve mikrofon izinleri isteniyor…</p>;

  if (status === "test")
    return (
      <div className="p-6 text-center">
        <Steps steps={["Aydınlatma", "İzinler", "Cihaz Testi", "Tanıtım", "Mülakat"]} current={2} className="mb-6 justify-center" />
        <h2 className="text-xl font-semibold">Cihaz Testi</h2>
        <div className="my-3">
          <strong>Tarayıcı İzinleri</strong>
          <p>Kamera: {camPerm || "?"} | Mikrofon: {micPerm || "?"}</p>
        </div>

        {/* Camera preview */}
        <video
          ref={videoRef}
          className="w-[240px] h-[180px] rounded-md object-cover bg-black mx-auto"
          playsInline
          autoPlay
          muted
        />
        <div className="mt-4">
          <label className="inline-flex items-center">
            <input
              type="checkbox"
              className="mr-2"
              checked={devicesOk}
              onChange={(e) => setDevicesOk(e.target.checked)}
            />
            Kameramı görüyorum ve mikrofonum çalışıyor.
          </label>
        </div>
        <Button className="mt-6" disabled={!devicesOk} onClick={() => setStatus("intro")}>İleri</Button>
      </div>
    );

  if (status === "permissionsDenied")
    return (
      <div className="p-6 text-center">
        <p>İzin alınamadı: {permissionError}</p>
        <Button className="mt-4" onClick={() => setStatus("permissions")}>Tekrar Dene</Button>
      </div>
    );

  // Intro step – show interview explanation and extra consent
  if (status === "intro") {
    return (
      <div className="max-w-xl mx-auto p-6">
        <Steps steps={["Aydınlatma", "İzinler", "Cihaz Testi", "Tanıtım", "Mülakat"]} current={3} className="mb-6" />
        <h2 className="text-xl font-semibold mb-2">Mülâkat Hakkında</h2>
        <p>
          Birazdan yapay zekâ destekli sesli bir görüşme başlayacak. Karşınızdaki avatar soruları sesli olarak soracak; siz de kameraya bakarak sesli yanıt vereceksiniz. Yanıtlarınız otomatik olarak metne dönüştürülecek ve sonraki sorular buna göre oluşturulacak.
        </p>
        <div className="mt-4 space-y-2">
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={showCaptions} onChange={(e)=> setShowCaptions(e.target.checked)} />
            Soru metinlerini göster (altyazı)
          </label>
        </div>
        <label className="block my-4">
          <input
            type="checkbox"
            className="mr-2"
            checked={ready}
            onChange={(e) => setReady(e.target.checked)}
          />
          Sürecin işleyişini anladım ve başlamak istiyorum.
        </label>
        <Button disabled={!ready} onClick={() => setStatus("interview")}>Görüşmeyi Başlat</Button>
      </div>
    );
  }

  if (status === "interview")
    return (
      <div className="p-6 text-center">
        <Steps steps={["Aydınlatma", "İzinler", "Cihaz Testi", "Tanıtım", "Mülakat"]} current={4} className="mb-6 justify-center" />
        <div className="mx-auto max-w-2xl mb-3 flex items-center justify-between text-sm text-gray-600">
          <div>
            Soru: {askedCount}
          </div>
          <div>
            Süre: {Math.floor(elapsedSec/60).toString().padStart(2,'0')}:{(elapsedSec%60).toString().padStart(2,'0')}
          </div>
        </div>
        <div className="flex gap-8 justify-center">
          {/* Avatar placeholder */}
          <div className="w-40 h-40 rounded-full bg-gray-200" />

          {/* Candidate preview */}
          <video
            ref={videoRef}
            className="w-40 h-40 rounded-full object-cover"
            playsInline
            autoPlay
            muted
          />
        </div>

        <p className="mt-6">
          {phase === "speaking" && "Soru soruluyor…"}
          {phase === "listening" && "Dinleniyor…"}
          {phase === "thinking" && "Yanıt işleniyor…"}
          {phase === "idle" && "Görüşme yakında başlayacak…"}
        </p>
        {question && showCaptions && (
          <div className="mt-3 max-w-2xl mx-auto text-gray-800 border border-gray-200 rounded-lg p-3 bg-white">
            <div className="text-sm font-medium text-gray-600 mb-1">Soru</div>
            <div className="text-base">{question}</div>
          </div>
        )}
        {/* Geçici Bitir butonu */}
        <Button
          className="mt-3"
          onClick={() => {
            setTimeout(() => {
              setPhase("idle");
              setStatus("finished");
            }, 3000); // 3 saniye kayıt yap, sonra bitir
          }}
        >
          Mülakatı Bitir (Test)
        </Button>
      </div>
    );

  if (status === "finished")
    return (
      <div className="p-6 text-center">
        <h2 className="text-xl font-semibold">Teşekkürler!</h2>
        <p className="text-gray-700 mt-2">Görüşmemize katıldığınız için teşekkür ederiz. Değerlendirmeniz yakında yapılacaktır.</p>
      </div>
    );

  return null; // fallback
}


function onVisibility(this: Document, ev: Event) {
  throw new Error("Function not implemented.");
}
// --- Conversation side effects (hooks must be after component definition) --- 