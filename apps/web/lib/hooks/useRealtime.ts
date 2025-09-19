"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { connectWebRTC, getEphemeralToken } from "@/lib/realtime";

export function useRealtime(interviewId?: number, token?: string) {
  const pcRef = useRef<RTCPeerConnection | null>(null);
  const audioElRef = useRef<HTMLAudioElement | null>(null);
  const dcRef = useRef<RTCDataChannel | null>(null);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const connect = useCallback(async () => {
    try {
      setError(null);
      const session = await getEphemeralToken(interviewId, token);
      const key = session.client_secret?.value || (session as any).value;
      if (!key) throw new Error("no_ephemeral_key");
      const { pc, audioEl, dc } = await connectWebRTC(key);
      pcRef.current = pc;
      audioElRef.current = audioEl;
      dcRef.current = dc || null;
      setConnected(true);
      return { pc, audioEl };
    } catch (e: any) {
      setError(e?.message || String(e));
      setConnected(false);
      return null;
    }
  }, [interviewId, token]);

  const disconnect = useCallback(() => {
    try { pcRef.current?.getSenders().forEach((s) => s.track?.stop()); } catch {}
    try { pcRef.current?.close(); } catch {}
    pcRef.current = null;
    audioElRef.current = null;
    setConnected(false);
  }, []);

  useEffect(() => () => { disconnect(); }, [disconnect]);

  return { connected, error, connect, disconnect, pcRef, audioElRef, dcRef } as const;
}


