"use client";
import { createContext, useContext, useState, ReactNode, useEffect } from "react";
import { apiFetch } from "@/lib/api";
import { useRouter } from "next/navigation";

interface UserProfile {
  id: number;
  email: string;
  is_admin: boolean;
  owner_user_id?: number | null;
  role?: string | null;
  can_manage_jobs: boolean;
  can_manage_candidates: boolean;
  can_view_interviews: boolean;
  can_manage_members: boolean;
}

interface AuthContextValue {
  token: string | null;
  user: UserProfile | null;
  login: (token: string, remember?: boolean) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<UserProfile | null>(null);
  const router = useRouter();

  // Helper to read token from sessionStorage first (if not remembered), then localStorage
  const readStoredToken = (): string | null => {
    try {
      const sess = typeof window !== "undefined" ? sessionStorage.getItem("token") : null;
      if (sess) return sess;
    } catch {}
    try {
      return typeof window !== "undefined" ? localStorage.getItem("token") : null;
    } catch {}
    return null;
  };

  // On first mount, check if a JWT is stored and still valid
  useEffect(() => {
    const stored = readStoredToken();
    if (!stored) return; // nothing to verify

    // Simply trust the stored token (will be validated on first API call)
    console.log("Found stored token, setting auth state");
    setToken(stored);
    // Load profile (includes permissions)
    (async () => {
      try {
        const me = await apiFetch<UserProfile>("/api/v1/auth/me", { skipRedirectOn401: true });
        setUser(me);
      } catch (e) {
        // token invalid; clear it
        localStorage.removeItem("token");
        try { sessionStorage.removeItem("dashboardData"); } catch {}
        setToken(null);
        setUser(null);
      }
    })();
  }, []);

  const login = (t: string, remember: boolean = true) => {
    // Persist to chosen storage
    try {
      // Clear both first to avoid ambiguity
      localStorage.removeItem("token");
      sessionStorage.removeItem("token");
    } catch {}
    try {
      if (remember) {
        localStorage.setItem("token", t);
      } else {
        sessionStorage.setItem("token", t);
      }
    } catch {}
    try { sessionStorage.removeItem("dashboardData"); } catch {}
    setToken(t);
    // Load profile then route
    (async () => {
      try { const me = await apiFetch<UserProfile>("/api/v1/auth/me", { skipRedirectOn401: true }); setUser(me); } catch {}
      router.push("/dashboard");
    })();
  };
  const logout = () => {
    try { localStorage.removeItem("token"); } catch {}
    try { sessionStorage.removeItem("token"); } catch {}
    try { sessionStorage.removeItem("dashboardData"); } catch {}
    setToken(null);
    setUser(null);
    router.push("/login");
  };
  return <AuthContext.Provider value={{ token, user, login, logout }}>{children}</AuthContext.Provider>;
}

export const useAuth = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("AuthContext missing");
  return ctx;
}; 