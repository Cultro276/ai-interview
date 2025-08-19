"use client";
import { useEffect, useState, useRef } from "react";
import { apiFetch } from "@/lib/api";
import { listen } from "@/lib/voice";
import { Steps } from "@/components/ui/Steps";
import { Button } from "@/components/ui/Button";

export default function InterviewPage({ params }: { params: { token: string } }) {
  const { token } = params;
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
  
  // Conversation tracking
  const [interviewId, setInterviewId] = useState<number | null>(null);
  const [interviewJobId, setInterviewJobId] = useState<number | null>(null);
  const sequenceNumberRef = useRef<number>(0);

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
      const interview = await apiFetch<{ id: number; job_id: number }>(`/api/v1/interviews/by-token/${token}`);
      setInterviewId(interview.id);
      setInterviewJobId(interview.job_id);
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

  // Schedule first question 2s after interview starts (fetch from backend using job context)
  useEffect(() => {
    if (status !== "interview" || question !== null) return;
    const id = setTimeout(() => {
      // Ask backend for the first question using empty history
      const initialHistory: { role: "assistant" | "user"; text: string }[] = [];
      apiFetch<{ question: string | null; done: boolean }>("/api/v1/interview/next-question", {
        method: "POST",
        body: JSON.stringify({ history: initialHistory, interview_id: interviewId }),
      })
        .then((res) => {
          const firstQuestion = (res.question || "").trim() || "Merhaba, kendinizi tanıtır mısınız?";
          setQuestion(firstQuestion);
          setHistory((h) => [...h, { role: "assistant", text: firstQuestion }]);
          setPhase("speaking");
          // Save first question to database
          saveConversationMessage("assistant", firstQuestion);
        })
        .catch(() => {
          const firstQuestion = "Merhaba, kendinizi tanıtır mısınız?";
          setQuestion(firstQuestion);
          setHistory((h) => [...h, { role: "assistant", text: firstQuestion }]);
          setPhase("speaking");
          saveConversationMessage("assistant", firstQuestion);
        });
    }, 2000);
    return () => clearTimeout(id);
  }, [status, question, interviewId]);

  // Speak current question and then listen for answer
  useEffect(() => {
    if (status !== "interview" || question === null) return;

    let rec: any = null;
    // Force ElevenLabs when available by adding provider in query body
    playTTS(question, () => {
      setPhase("listening");

      let buffer: string[] = [];
      let silenceTimer: any = null;
      let hardStopTimer: any = null;

      const finalize = () => {
        if (rec && rec.stop) rec.stop();
        if (silenceTimer) clearTimeout(silenceTimer);
        if (hardStopTimer) clearTimeout(hardStopTimer);
        let full = buffer.join(" ").trim();
        if (!full) {
          // Fallback: proceed even if no speech captured, to avoid getting stuck
          full = "...";
        }

        // Update history with user's answer
        const newHistoryLocal = [...history, { role: "user", text: full }];
        setHistory(newHistoryLocal);
        setPhase("thinking");

        // Save user's answer to database
        saveConversationMessage("user", full);

        apiFetch<{ question: string | null; done: boolean }>(
          "/api/v1/interview/next-question",
          {
            method: "POST",
            body: JSON.stringify({ history: newHistoryLocal, interview_id: interviewId }),
          },
        )
          .then((res) => {
            if (res.done) {
              setPhase("idle");
              setStatus("finished");
              // Save completion message
              saveConversationMessage("system", "Interview completed");
            } else {
              const nextQ = (res.question || "").trim() || "Devam edelim: Son projende üstlendiğin rolü biraz açabilir misin?";
              setQuestion(nextQ);
              setHistory((h) => [...h, { role: "assistant", text: nextQ }]);
              setPhase("speaking");
              // Save AI's next question
              saveConversationMessage("assistant", nextQ);
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
      rec = listen(
        (t) => {
          buffer.push(t);
          // Each time we get speech, reset the timer to wait for next words
          if (silenceTimer) clearTimeout(silenceTimer);
          // Enforce a minimum listening window of 2s to avoid immediate finalize
          const minHold = Math.max(0, 2000 - (Date.now() - listenStart));
          silenceTimer = setTimeout(finalize, 4000 + minHold);
        },
      );

      // Safety net: if STT yields nothing (no events), force finalize after 12s
      hardStopTimer = setTimeout(finalize, 12000);
    });

    return () => {
      if (rec && rec.stop) rec.stop();
      try { currentTtsSourceRef.current?.stop(0); } catch {}
    };
  }, [status, question]);

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
          "audio/webm;codecs=opus",
          "audio/webm",
          "audio/ogg;codecs=opus",
          "audio/mp4",
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
        <label className="block my-4">
          <input
            type="checkbox"
            className="mr-2"
            checked={accepted}
            onChange={(e) => setAccepted(e.target.checked)}
          />
          KVKK metnini okudum ve kabul ediyorum.
        </label>
        <Button disabled={!accepted} onClick={() => setStatus("permissions")}>Devam Et</Button>
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
        {question && (
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

// --- Conversation side effects (hooks must be after component definition) --- 