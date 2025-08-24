export type SpeechTranscriptCallback = (text: string) => void;

// Text-to-Speech: Prefer server provider (e.g., ElevenLabs/Azure) for consistent audio
export async function speak(text: string, onEnd?: () => void, lang = "tr-TR") {
  // Build API base
  const baseFromEnv = (process as any)?.env?.NEXT_PUBLIC_API_URL as string | undefined;
  const baseFromWindow =
    typeof window !== "undefined"
      ? `${window.location.protocol}//${window.location.hostname}:8000`
      : "";
  const base = ((baseFromEnv && baseFromEnv.trim().length > 0 ? baseFromEnv : baseFromWindow) || "").replace(/\/+$/g, "");

  // If no window, just signal completion
  if (typeof window === "undefined") {
    onEnd?.();
    return;
  }

  try {
    const res = await fetch(`${base}/api/v1/tts/speak`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      // Server auto-selects provider (prefers ElevenLabs if configured)
      body: JSON.stringify({ text, lang: (lang || "tr-TR").slice(0, 2) }),
    });
    if (!res.ok) throw new Error(`TTS ${res.status}`);
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const audio = new Audio(url);
    audio.onended = () => {
      try { URL.revokeObjectURL(url); } catch {}
      onEnd?.();
    };
    audio.onerror = () => {
      try { URL.revokeObjectURL(url); } catch {}
      onEnd?.();
    };
    // Attempt playback; if blocked by user gesture policy, still proceed after a grace time
    let played = false;
    try {
      await audio.play();
      played = true;
    } catch {
      // Autoplay blocked; start a short timer and call onEnd so flow continues
      setTimeout(() => onEnd?.(), 1200);
    }
    if (!played) {
      // As a last resort, try browser TTS briefly to give some audible feedback
      try {
        if ("speechSynthesis" in window) {
          (window as any).speechSynthesis.cancel();
          const utter = new (window as any).SpeechSynthesisUtterance(text);
          utter.lang = lang;
          utter.onend = () => onEnd?.();
          (window as any).speechSynthesis.speak(utter);
        }
      } catch {
        // Ignore, onEnd already scheduled
      }
    }
  } catch {
    // On error, still advance the flow to avoid hanging state
    onEnd?.();
  }
}

// Start Speech-to-Text (speech recognition). Returns the recognition instance so caller can stop() later.
export function listen(
  onResult: SpeechTranscriptCallback,
  onSpeechEnd?: () => void,
  lang = "tr-TR",
) {
  if (typeof window === "undefined") return null;
  const SpeechRecognition =
    (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
  if (!SpeechRecognition) {
    console.error("SpeechRecognition API not supported in this browser");
    return null;
  }
  const recognition = new SpeechRecognition();
  recognition.lang = lang;
  // Use partials to detect speech boundaries more reliably
  recognition.interimResults = true;
  recognition.continuous = true;
  recognition.maxAlternatives = 1;

  recognition.onresult = (e: any) => {
    const idx = e.results.length - 1;
    const res = e.results[idx];
    const transcript = res[0].transcript;
    // Emit only final results to the caller buffer to avoid early advancement
    if (res.isFinal) {
      onResult(transcript);
    }
  };

  if (onSpeechEnd) {
    recognition.onspeechend = onSpeechEnd;
    recognition.onend = onSpeechEnd;
  }
  
  recognition.start();
  return recognition;
} 