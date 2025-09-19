// Centralized frontend configuration helpers (no new .env creation)

export function readEnv(key: string): string | undefined {
  try {
    const v = (globalThis as any)?.process?.env?.[key];
    return typeof v === "string" ? v : undefined;
  } catch {
    return undefined;
  }
}

export function getApiBaseUrl(): string {
  const fromEnv = readEnv("NEXT_PUBLIC_API_URL");
  const fromWindow = typeof window !== "undefined" ? `${window.location.protocol}//${window.location.hostname}:8000` : "";
  return (fromEnv && fromEnv.trim().length > 0 ? fromEnv : fromWindow).replace(/\/+$/g, "");
}

export function getOpenAIRealtimeBaseUrl(): string {
  const fromEnv = readEnv("NEXT_PUBLIC_OPENAI_REALTIME_URL");
  const fallback = "https://api.openai.com/v1/realtime";
  const base = (fromEnv && fromEnv.trim().length > 0 ? fromEnv : fallback).replace(/\/+$/g, "");
  return base;
}

export function getOpenAIRealtimeModel(): string {
  return readEnv("NEXT_PUBLIC_OPENAI_REALTIME_MODEL") || "gpt-4o-realtime-preview";
}


