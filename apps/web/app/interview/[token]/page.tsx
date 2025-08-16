"use client";
import { useEffect, useState, useRef } from "react";
import { apiFetch } from "@/lib/api";
import { speak, listen } from "@/lib/voice";

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
  const sequenceNumberRef = useRef<number>(0);

  const videoRef = useRef<HTMLVideoElement>(null);

  // Save conversation message to database (no-redirect for unauthenticated candidate)
  const saveConversationMessage = async (role: "assistant" | "user" | "system", content: string) => {
    if (!interviewId) return;
    try {
      sequenceNumberRef.current += 1;
      const base = (process.env.NEXT_PUBLIC_API_URL || `${window.location.protocol}//${window.location.hostname}:8000`).replace(/\/+$/g, "");
      await fetch(`${base}/api/v1/conversations/messages`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          interview_id: interviewId,
          role,
          content,
          sequence_number: sequenceNumberRef.current,
        }),
      });
    } catch (error) {
      // best-effort only in candidate UI
    }
  };

  // Get or create interview record and save initial system message
  const initializeInterview = async () => {
    try {
      // First, try to get existing interview for this candidate
      const candidate = await apiFetch<any>(`/api/v1/tokens/candidate?token=${token}`);
      
      // For now, we'll create the interview record when we upload media
      // The interview ID will be available after the first media upload
      console.log("Interview initialization will happen on media upload");
      
      // Save system message to indicate interview started
      const systemMessage = `Interview started at ${new Date().toISOString()}`;
      sequenceNumberRef.current = 0;
      // We'll save this when we have interview_id
      
    } catch (error) {
      console.error("Failed to initialize interview:", error);
    }
  };

  // Verify the token once on mount
  useEffect(() => {
    apiFetch(`/api/v1/tokens/verify?token=${token}`, { method: "POST" })
      .then(() => setStatus("consent"))
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

  // Stop recording & upload when interview finishes
  useEffect(() => {
    if (status !== "finished") return;

    const upload = async () => {
      try {
        // Simple stop
        mediaRecorderRef.current?.stop();
        audioRecorderRef.current?.stop();
        
        // Wait for chunks
        await new Promise(r => setTimeout(r, 1000));

        const videoBlob = new Blob(videoChunksRef.current, { type: "video/webm" });
        const audioBlob = new Blob(audioChunksRef.current, { type: "audio/webm" });

        console.log("Video size", videoBlob.size, "bytes", "Audio size", audioBlob.size);

        // Proceed even if one of the blobs is empty; we'll still mark completion

        const uploadOne = async (blob: Blob, kind: "video" | "audio") => {
          const fileName = `${kind}-${Date.now()}.webm`;
          const presign = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/tokens/presign-upload`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ token, file_name: fileName, content_type: blob.type }),
          }).then(async (r) => {
            if (!r.ok) {
              const text = await r.text();
              throw new Error(`Presign failed ${r.status}: ${text}`);
            }
            return r.json();
          });
          await fetch(presign.presigned_url || presign.url, { method: "PUT", body: blob, headers: { "Content-Type": blob.type } }).then(async r => {
            if(!r.ok){
              const text = await r.text();
              throw new Error(`S3 upload failed ${r.status}: ${text}`);
            }
          });
          const baseUrl = (presign.presigned_url || presign.url).split('?')[0];
          return baseUrl.startsWith('http') ? baseUrl : `s3://${presign.key}`;
        };

        let videoUrl: string | null = null;
        let audioUrl: string | null = null;
        try {
          if (videoBlob.size > 0) {
            videoUrl = await uploadOne(videoBlob, "video");
          }
        } catch (e) {
          console.error("Video upload failed", e);
        }
        try {
          if (audioBlob.size > 0) {
            audioUrl = await uploadOne(audioBlob, "audio");
          }
        } catch (e) {
          console.error("Audio upload failed", e);
        }

        // Save URLs to interview (no auth needed)
        const resp = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/interviews/${token}/media`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ video_url: videoUrl, audio_url: audioUrl }),
        });
        try {
          if (resp.ok) {
            const data = await resp.json();
            if (data && typeof data.id === 'number') setInterviewId(data.id);
          }
        } catch {}
      } catch (err) {
        console.error("Upload error", err);
        // Try to at least mark interview completed without media
        try {
          await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/interviews/${token}/media`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ video_url: null, audio_url: null }),
          });
        } catch {}
      }
    };

    upload();
  }, [status, token]);

  // Query permission states once we reach test step
  useEffect(() => {
    if (status !== "test" || !navigator.permissions) return;
    navigator.permissions.query({ name: "camera" as PermissionName }).then((p) => setCamPerm(p.state));
    navigator.permissions.query({ name: "microphone" as PermissionName }).then((p) => setMicPerm(p.state));
  }, [status]);

  // Schedule first question 2s after interview starts
  useEffect(() => {
    if (status !== "interview" || question !== null) return;
    const id = setTimeout(() => {
      const firstQuestion = "Merhaba, kendinizi tanıtır mısınız?";
      setQuestion(firstQuestion);
      setHistory((h) => [...h, { role: "assistant", text: firstQuestion }]);
      setPhase("speaking");
      
      // Save first question to database
      saveConversationMessage("assistant", firstQuestion);
    }, 2000);
    return () => clearTimeout(id);
  }, [status, question, interviewId]);

  // Speak current question and then listen for answer
  useEffect(() => {
    if (status !== "interview" || question === null) return;

    let rec: any = null;
    speak(question, () => {
      setPhase("listening");

      let buffer: string[] = [];
      let silenceTimer: any = null;

      const finalize = () => {
        if (rec && rec.stop) rec.stop();
        const full = buffer.join(" ").trim();
        if (!full) return; // nothing captured

        // Update history with user's answer
        setHistory((h) => [...h, { role: "user", text: full }]);
        setPhase("thinking");

        // Save user's answer to database
        saveConversationMessage("user", full);

        apiFetch<{ question: string | null; done: boolean }>(
          "/api/v1/interview/next-question",
          {
            method: "POST",
            body: JSON.stringify({ history: [...history, { role: "user", text: full }] }),
          },
        )
          .then((res) => {
            if (res.done) {
              setPhase("idle");
              setStatus("finished");
              // Save completion message
              saveConversationMessage("system", "Interview completed");
            } else if (res.question) {
              setQuestion(res.question);
              setHistory((h) => [...h, { role: "assistant", text: res.question! }]);
              setPhase("speaking");
              // Save AI's next question
              saveConversationMessage("assistant", res.question);
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

      rec = listen(
        (t) => {
          buffer.push(t);
          // Each time we get speech, reset the timer to wait for next words
          if (silenceTimer) clearTimeout(silenceTimer);
          silenceTimer = setTimeout(finalize, 4000); // 4 seconds of no new speech triggers finalize
        },
      );
    });

    return () => {
      if (rec && rec.stop) rec.stop();
      if (typeof window !== "undefined" && "speechSynthesis" in window) {
        window.speechSynthesis.cancel();
      }
    };
  }, [status, question]);

  // --- Start recording when interview begins ---
  // 1) Video+Audio recorder
  useEffect(() => {
    if (status !== "interview" || !stream) return;
    try {
      console.log("Starting recording with stream tracks:", stream.getTracks().length);
      const rec = new MediaRecorder(stream);
      rec.ondataavailable = (e) => {
        console.log("video chunk", e.data.size);
        videoChunksRef.current.push(e.data);
      };
      rec.start();
      mediaRecorderRef.current = rec;

      // 2) Audio-only recorder (clone only audio tracks)
      const audioTracks = stream.getAudioTracks();
      if (audioTracks.length) {
        const audioOnlyStream = new MediaStream(audioTracks);
        const audioRec = new MediaRecorder(audioOnlyStream);
        audioRec.ondataavailable = (e) => {
          console.log("audio chunk", e.data.size);
          audioChunksRef.current.push(e.data);
        };
        audioRec.start();
        audioRecorderRef.current = audioRec;
      }
    } catch (e) {
      console.error("MediaRecorder error:", e);
    }
  }, [status, stream]);

  if (status === "loading") return <p>Doğrulanıyor…</p>;
  if (status === "invalid") return <p>{error || "Bağlantı geçersiz veya süresi dolmuş."}</p>;

  if (status === "consent") {
    return (
      <div style={{ padding: "2rem", maxWidth: "600px", margin: "0 auto" }}>
        <h1>KVKK Aydınlatma Metni</h1>
        <p>
          Bu video mülâkat sırasında kaydedilen görüntü ve ses verileriniz, işe alım
          sürecinin yürütülmesi amacıyla işlenecek ve saklanacaktır.
        </p>
        <label style={{ display: "block", margin: "1rem 0" }}>
          <input
            type="checkbox"
            checked={accepted}
            onChange={(e) => setAccepted(e.target.checked)}
          />
          &nbsp; KVKK metnini okudum ve kabul ediyorum.
        </label>
        <button disabled={!accepted} onClick={() => setStatus("permissions")}>Devam Et</button>
      </div>
    );
  }

  // permissions step placeholder – will handle camera/mic permissions next
  if (status === "permissions") return <p>Kamera ve mikrofon izinleri isteniyor…</p>;

  if (status === "test")
    return (
      <div style={{ padding: "2rem", textAlign: "center" }}>
        <h2>Cihaz Testi</h2>
        <div style={{ marginBottom: "1rem" }}>
          <strong>Tarayıcı İzinleri</strong>
          <p>Kamera: {camPerm || "?"} | Mikrofon: {micPerm || "?"}</p>
        </div>

        {/* Camera preview */}
        <video
          ref={videoRef}
          style={{ width: 240, height: 180, borderRadius: 8, objectFit: "cover", background: "#000" }}
          playsInline
          autoPlay
          muted
        />
        <div style={{ marginTop: "1rem" }}>
          <label>
            <input
              type="checkbox"
              checked={devicesOk}
              onChange={(e) => setDevicesOk(e.target.checked)}
            />
            &nbsp; Kameramı görüyorum ve mikrofonum çalışıyor.
          </label>
        </div>
        <button style={{ marginTop: "1.5rem" }} disabled={!devicesOk} onClick={() => setStatus("intro")}>İleri</button>
      </div>
    );

  if (status === "permissionsDenied")
    return (
      <div style={{ padding: "2rem", textAlign: "center" }}>
        <p>İzin alınamadı: {permissionError}</p>
        <button onClick={() => setStatus("permissions")}>Tekrar Dene</button>
      </div>
    );

  // Intro step – show interview explanation and extra consent
  if (status === "intro") {
    return (
      <div style={{ padding: "2rem", maxWidth: "600px", margin: "0 auto" }}>
        <h2>Mülâkat Hakkında</h2>
        <p>
          Birazdan yapay zekâ destekli sesli bir görüşme başlayacak. Karşınızdaki avatar
          soruları sesli olarak soracak; siz de kameraya bakarak sesli yanıt vereceksiniz.
          Yanıtlarınız otomatik olarak metne dönüştürülecek ve sonraki sorular buna göre
          oluşturulacak.
        </p>
        <label style={{ display: "block", margin: "1rem 0" }}>
          <input
            type="checkbox"
            checked={ready}
            onChange={(e) => setReady(e.target.checked)}
          />
          &nbsp; Sürecin işleyişini anladım ve başlamak istiyorum.
        </label>
        <button disabled={!ready} onClick={() => setStatus("interview")}>Görüşmeyi Başlat</button>
      </div>
    );
  }

  if (status === "interview")
    return (
      <div style={{ padding: "2rem", textAlign: "center" }}>
        <div style={{ display: "flex", gap: "2rem", justifyContent: "center" }}>
          {/* Avatar placeholder */}
          <div style={{ width: 160, height: 160, borderRadius: "50%", background: "#eee" }} />

          {/* Candidate preview */}
          <video
            ref={videoRef}
            style={{ width: 160, height: 160, borderRadius: "50%", objectFit: "cover" }}
            playsInline
            autoPlay
            muted
          />
        </div>

        <p style={{ marginTop: "1.5rem" }}>
          {phase === "speaking" && "Soru soruluyor…"}
          {phase === "listening" && "Dinleniyor…"}
          {phase === "thinking" && "Yanıt işleniyor…"}
          {phase === "idle" && "Görüşme yakında başlayacak…"}
        </p>
        {/* Geçici Bitir butonu */}
        <button
          style={{ marginTop: "1rem", padding: "0.5rem 1rem" }}
          onClick={() => {
            setTimeout(() => {
              setPhase("idle");
              setStatus("finished");
            }, 3000); // 3 saniye kayıt yap, sonra bitir
          }}
        >
          Mülakatı Bitir (Test)
        </button>
      </div>
    );

  if (status === "finished")
    return (
      <div style={{ padding: "2rem", textAlign: "center" }}>
        <h2>Teşekkürler!</h2>
        <p>Görüşmemize katıldığınız için teşekkür ederiz. Değerlendirmeniz yakında yapılacaktır.</p>
      </div>
    );

  // Upload media when interview finishes
  useEffect(() => {
    if (status !== "finished") return;
    
    const uploadMedia = async () => {
      try {
        console.log("Starting media upload...");
        
        // Stop recorders and get final data
        if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
          mediaRecorderRef.current.stop();
          await new Promise(resolve => {
            mediaRecorderRef.current!.addEventListener("stop", resolve, { once: true });
          });
        }
        
        if (audioRecorderRef.current && audioRecorderRef.current.state !== "inactive") {
          audioRecorderRef.current.stop();
          await new Promise(resolve => {
            audioRecorderRef.current!.addEventListener("stop", resolve, { once: true });
          });
        }
        
        // Create blobs from chunks
        const videoBlob = new Blob(videoChunksRef.current, { type: "video/webm" });
        const audioBlob = new Blob(audioChunksRef.current, { type: "audio/webm" });
        
        console.log("Video blob size:", videoBlob.size, "Audio blob size:", audioBlob.size);
        
        if (videoBlob.size === 0 && audioBlob.size === 0) {
          console.log("No media data to upload");
          return;
        }
        
        // Get presigned URLs
        const videoPresignedUrl = videoBlob.size > 0 ? await apiFetch<{ presigned_url: string }>("/api/v1/tokens/presign-upload", {
          method: "POST",
          body: JSON.stringify({
            file_name: `interview-${token}-video-${Date.now()}.webm`,
            content_type: "video/webm"
          })
        }) : null;
        
        const audioPresignedUrl = audioBlob.size > 0 ? await apiFetch<{ presigned_url: string }>("/api/v1/tokens/presign-upload", {
          method: "POST",
          body: JSON.stringify({
            file_name: `interview-${token}-audio-${Date.now()}.webm`,
            content_type: "audio/webm"
          })
        }) : null;
        
        // Upload to S3
        const uploads = [];
        
        if (videoPresignedUrl && videoBlob.size > 0) {
          uploads.push(
            fetch(videoPresignedUrl.presigned_url, {
              method: "PUT",
              body: videoBlob,
              headers: { "Content-Type": "video/webm" }
            })
          );
        }
        
        if (audioPresignedUrl && audioBlob.size > 0) {
          uploads.push(
            fetch(audioPresignedUrl.presigned_url, {
              method: "PUT", 
              body: audioBlob,
              headers: { "Content-Type": "audio/webm" }
            })
          );
        }
        
        if (uploads.length > 0) {
          await Promise.all(uploads);
          console.log("Media uploaded to S3 successfully");
        }
        
        // Save media URLs to interview record and get interview ID
        const videoUrl = videoPresignedUrl ? videoPresignedUrl.presigned_url.split('?')[0] : null;
        const audioUrl = audioPresignedUrl ? audioPresignedUrl.presigned_url.split('?')[0] : null;
        
        const interviewRecord = await apiFetch<{ id: number }>(`/api/v1/interviews/${token}/media`, {
          method: "PATCH",
          body: JSON.stringify({
            video_url: videoUrl,
            audio_url: audioUrl
          })
        });
        
        // Now we have the interview ID! Save it and initialize conversation tracking
        setInterviewId(interviewRecord.id);
        console.log("Interview ID captured:", interviewRecord.id);
        
        // Save system message about interview completion
        if (interviewRecord.id) {
          await apiFetch("/api/v1/conversations/messages", {
            method: "POST",
            body: JSON.stringify({
              interview_id: interviewRecord.id,
              role: "system",
              content: `Interview completed. Media uploaded: video=${videoUrl ? 'yes' : 'no'}, audio=${audioUrl ? 'yes' : 'no'}`,
              sequence_number: sequenceNumberRef.current + 1
            })
          });
        }
        
      } catch (error) {
        console.error("Media upload failed:", error);
      }
    };
    
    uploadMedia();
  }, [status, token]);

  return null; // fallback
}

// --- Conversation side effects (hooks must be after component definition) --- 