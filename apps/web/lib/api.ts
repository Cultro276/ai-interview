import Router from "next/router";

export async function apiFetch<T>(
  url: string,
  options: RequestInit = {},
): Promise<T> {
  const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
  const headers: Record<string, string> = {
    ...(options.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
    ...(options.headers as Record<string, string>),
  };
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  // Resolve API base URL with solid fallback for all environments
  const baseFromEnv = process.env.NEXT_PUBLIC_API_URL;
  const baseFromWindow =
    typeof window !== "undefined"
      ? `${window.location.protocol}//${window.location.hostname}:8000`
      : "";
  const base = (baseFromEnv && baseFromEnv.trim().length > 0 ? baseFromEnv : baseFromWindow).replace(/\/+$/g, "");
  const path = url.startsWith("/") ? url : `/${url}`;
  const fullUrl = `${base}${path}`;

  const res = await fetch(fullUrl, {
    ...options,
    headers,
  });
  if (res.status === 401) {
    if (typeof window !== "undefined") Router.push("/login");
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