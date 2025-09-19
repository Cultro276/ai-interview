import { getApiBaseUrl, getOpenAIRealtimeBaseUrl, getOpenAIRealtimeModel } from "@/lib/config";

export type RealtimeSession = {
  client_secret: { value: string; expires_at: number };
  model: string;
  voice?: string;
};

export async function getEphemeralToken(interviewId?: number, token?: string, model?: string, voice?: string) {
  const base = getApiBaseUrl();
  const res = await fetch(`${base}/api/v1/realtime/ephemeral`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ interview_id: interviewId, token, model, voice }),
  });
  if (!res.ok) throw new Error(`ephemeral ${res.status}`);
  return (await res.json()) as RealtimeSession;
}

export async function connectWebRTC(ephemeralKey: string) {
  const pc = new RTCPeerConnection();
  const audioEl = document.createElement("audio");
  audioEl.autoplay = true;
  pc.ontrack = (e) => {
    audioEl.srcObject = e.streams[0];
  };

  // Mic capture
  const ms = await navigator.mediaDevices.getUserMedia({ audio: true });
  for (const track of ms.getTracks()) pc.addTrack(track, ms);

  // Data channel for events (optional)
  const dc = pc.createDataChannel("oai-events");
  dc.onmessage = (ev) => {
    // Handle model events if needed
    try { const msg = JSON.parse(ev.data); console.debug("oai", msg); } catch {}
  };

  const offer = await pc.createOffer({ offerToReceiveAudio: true });
  await pc.setLocalDescription(offer);

  const base = getOpenAIRealtimeBaseUrl();
  const model = getOpenAIRealtimeModel();
  const url = `${base}?model=${encodeURIComponent(model)}`;
  const sdpRes = await fetch(url, {
    method: "POST",
    body: offer.sdp,
    headers: {
      Authorization: `Bearer ${ephemeralKey}`,
      "Content-Type": "application/sdp",
      "OpenAI-Beta": "realtime=v1",
    },
  });
  if (!sdpRes.ok) throw new Error(`realtime sdp ${sdpRes.status}`);
  const answer = { type: "answer", sdp: await sdpRes.text() } as RTCSessionDescriptionInit;
  await pc.setRemoteDescription(answer);

  return { pc, audioEl, dc };
}


