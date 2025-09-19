// Avoid importing next/router in App Router; redirect via window
import { getApiBaseUrl } from "@/lib/config";

export async function apiFetch<T>(
  url: string,
  options: RequestInit & { skipRedirectOn401?: boolean } = {},
): Promise<T> {
  // Read token from sessionStorage first (non-remembered sessions), then localStorage
  const token = typeof window !== "undefined"
    ? (sessionStorage.getItem("token") || localStorage.getItem("token"))
    : null;
  const foundersSecret = typeof window !== "undefined" ? localStorage.getItem("founders_secret") : null;
  // Allow caller to opt out of JSON content-type via options.headers
  const headers: Record<string, string> = {
    ...(options.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
    ...(options.headers as Record<string, string>),
  };
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  if (foundersSecret) {
    headers["x-internal-secret"] = foundersSecret;
  }

  // Resolve API base URL via centralized config
  const base = getApiBaseUrl();
  const path = url.startsWith("/") ? url : `/${url}`;
  const fullUrl = `${base}${path}`;

  const res = await fetch(fullUrl, {
    ...options,
    headers,
  });
  if (res.status === 401) {
    if (!options.skipRedirectOn401) {
      if (typeof window !== "undefined") window.location.href = "/login";
    }
    throw new Error("Unauthorized");
  }
  if (!res.ok) {
    let message = "Error";
    try {
      const err = await res.json();
      if (typeof err?.detail === "string") {
        message = err.detail;
      } else if (Array.isArray(err?.detail)) {
        // FastAPI validation errors: map to readable string
        message = err.detail
          .map((e: any) => {
            const loc = Array.isArray(e?.loc) ? e.loc.join(".") : e?.loc;
            return [loc, e?.msg].filter(Boolean).join(": ");
          })
          .join(", ");
      } else if (err) {
        message = JSON.stringify(err);
      }
    } catch {}
    throw new Error(message);
  }
  return res.status === 204 ? ({} as T) : res.json();
} 

export function sseStream(
  path: string,
  onDelta: (data: any) => void,
  onDone?: () => void,
  onError?: (e: any) => void,
) {
  const baseFromEnv = process.env.NEXT_PUBLIC_API_URL;
  const baseFromWindow =
    typeof window !== "undefined"
      ? `${window.location.protocol}//${window.location.hostname}:8000`
      : "";
  const base = (baseFromEnv && baseFromEnv.trim().length > 0 ? baseFromEnv : baseFromWindow).replace(/\/+$/g, "");
  const fullPath = path.startsWith("/") ? path : `/${path}`;
  const url = `${base}${fullPath}`;

  const es = new EventSource(url);
  es.addEventListener("delta", (ev) => {
    try {
      onDelta(JSON.parse((ev as MessageEvent).data));
    } catch {
      onDelta((ev as MessageEvent).data);
    }
  });
  es.addEventListener("done", () => {
    try {
      onDone?.();
    } finally {
      es.close();
    }
  });
  es.addEventListener("error", (e) => {
    try {
      onError?.(e);
    } finally {
      es.close();
    }
  });
  return () => es.close();
}