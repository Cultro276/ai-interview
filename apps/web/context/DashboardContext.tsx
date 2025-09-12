"use client";
import React, { createContext, useContext, useState, useEffect, useRef, ReactNode } from 'react';
import { apiFetch } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";

interface Job {
  id: number;
  title: string;
  description: string;
  created_at: string;
}

interface Candidate {
  id: number;
  name: string;
  email: string;
  phone?: string;
  linkedin_url?: string;
  resume_url?: string;
  job_id?: number;
  token: string;
  expires_at: string;
  created_at: string;
}

interface Interview {
  id: number;
  job_id: number;
  candidate_id: number;
  status: string;
  created_at: string;
  completed_at?: string;
  audio_url?: string;
  video_url?: string;
  candidate?: Candidate;
  job?: Job;
}

interface DashboardContextType {
  candidates: Candidate[];
  jobs: Job[];
  interviews: Interview[];
  loading: boolean;
  dataLoaded: boolean;
  refreshData: () => Promise<void>;
}

const DashboardContext = createContext<DashboardContextType | undefined>(undefined);

export function DashboardProvider({ children }: { children: ReactNode }) {
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [interviews, setInterviews] = useState<Interview[]>([]);
  const [loading, setLoading] = useState(true);
  const [dataLoaded, setDataLoaded] = useState(false);
  const { user, token } = useAuth();

  const cacheKey = typeof window !== 'undefined' && user ? `dashboardData:${user.id}` : null;
  const notifiedKey = typeof window !== 'undefined' && user ? `notifiedAnalyses:${user.id}` : null;
  const viewedKey = typeof window !== 'undefined' && user ? `viewedAnalyses:${user.id}` : null;
  const notifiedRef = useRef<Set<number>>(new Set());
  const viewedRef = useRef<Set<number>>(new Set());

  const loadData = async () => {
    try {
      // Skip API calls if there is no auth token (e.g., on /login)
      const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
      if (!token) {
        console.warn("No authentication token found - skipping API calls");
        setDataLoaded(true);
        setLoading(false);
        return;
      }
      
      console.log("Loading dashboard data with token:", token.substring(0, 10) + "...");
      
      const [candidatesRes, jobsRes, interviewsRes] = await Promise.allSettled([
        apiFetch<Candidate[]>("/api/v1/candidates/"),
        apiFetch<Job[]>("/api/v1/jobs/"),
        apiFetch<Interview[]>("/api/v1/interviews/"),
      ]);

      // Enhanced error handling for debugging
      if (candidatesRes.status === "rejected") {
        console.error("Failed to load candidates:", candidatesRes.reason);
      }
      if (jobsRes.status === "rejected") {
        console.error("Failed to load jobs:", jobsRes.reason);
      }
      if (interviewsRes.status === "rejected") {
        console.error("Failed to load interviews:", interviewsRes.reason);
      }

      const nextCandidates = candidatesRes.status === "fulfilled" ? (candidatesRes.value || []) : [];
      const nextJobs = jobsRes.status === "fulfilled" ? (jobsRes.value || []) : [];
      const nextInterviews = interviewsRes.status === "fulfilled" ? (interviewsRes.value || []) : [];

      setCandidates(nextCandidates);
      setJobs(nextJobs);
      setInterviews(nextInterviews);

      // Save per-user backup cache
      if (typeof window !== 'undefined' && cacheKey) {
        sessionStorage.setItem(cacheKey, JSON.stringify({
          candidates: nextCandidates,
          jobs: nextJobs,
          interviews: nextInterviews,
        }));
      }

      setDataLoaded(true);
    } catch (error) {
      console.error("Failed to load data:", error);

      // Try to load from session storage on error
      if (typeof window !== 'undefined') {
        const savedData = sessionStorage.getItem('dashboardData');
        if (savedData) {
          try {
            const { candidates: savedCandidates, jobs: savedJobs, interviews: savedInterviews } = JSON.parse(savedData);
            setCandidates(savedCandidates || []);
            setJobs(savedJobs || []);
            setInterviews(savedInterviews || []);
          } catch (e) {
            // ignore JSON parse error
          }
        }
      }

      setDataLoaded(true);
    } finally {
      setLoading(false);
    }
  };

  const refreshData = async () => {
    setLoading(true);
    await loadData();
  };

  useEffect(() => {
    if (!dataLoaded) {
      // If no token, don't attempt initial load
      if (typeof window !== 'undefined') {
        const token = localStorage.getItem('token');
        if (!token) {
          setDataLoaded(true);
          setLoading(false);
          return;
        }
      }
      // Try to load from session storage first
      if (typeof window !== 'undefined' && cacheKey) {
        const savedData = sessionStorage.getItem(cacheKey);
        if (savedData) {
          try {
            const { candidates: savedCandidates, jobs: savedJobs, interviews: savedInterviews } = JSON.parse(savedData);
            setCandidates(savedCandidates || []);
            setJobs(savedJobs || []);
            setInterviews(savedInterviews || []);
            // Do not return early; kick off a background refresh to avoid stale cache
            setDataLoaded(true);
            setLoading(false);
            // Reconcile with server in background
            loadData();
            return;
          } catch (e) {
            //
          }
        }
      }
      
      // If no saved data, load from API
      loadData();
    }
  }, [dataLoaded, cacheKey]);

  // On user or token change, reset data to avoid cross-tenant leakage
  useEffect(() => {
    if (typeof window !== 'undefined') {
      // Best-effort: clear old generic cache key if present
      try { sessionStorage.removeItem('dashboardData'); } catch {}
    }
    setCandidates([]);
    setJobs([]);
    setInterviews([]);
    setDataLoaded(false);
  }, [user?.id, token]);

  // Load previously notified/viewed analysis ids (persist across sessions using localStorage)
  useEffect(() => {
    if (typeof window === 'undefined' || !notifiedKey) return;
    try {
      const raw = localStorage.getItem(notifiedKey);
      if (raw) {
        const arr: number[] = JSON.parse(raw);
        notifiedRef.current = new Set(Array.isArray(arr) ? arr : []);
      }
    } catch {}
    try {
      const raw2 = viewedKey ? localStorage.getItem(viewedKey) : null;
      if (raw2) {
        const arr2: number[] = JSON.parse(raw2);
        viewedRef.current = new Set(Array.isArray(arr2) ? arr2 : []);
      }
    } catch {}
  }, [notifiedKey]);

  // Attempt to show a browser notification (graceful no-op if blocked)
  const tryShowNotification = (title: string, body: string, url?: string) => {
    if (typeof window === 'undefined' || !("Notification" in window)) return;
    const show = () => {
      try {
        const n = new Notification(title, { body, icon: "/logo.png" });
        if (url) {
          n.onclick = () => {
            try { window.focus(); } catch {}
            try { window.open(url, "_blank"); } catch {}
          };
        }
      } catch {}
    };
    if (Notification.permission === 'granted') {
      show();
    } else if (Notification.permission === 'default') {
      try {
        Notification.requestPermission().then((perm) => {
          if (perm === 'granted') show();
        });
      } catch {}
    }
  };

  // Detect newly completed interviews, ensure analysis exists, then notify once (aggregated)
  useEffect(() => {
    if (!dataLoaded || !interviews?.length) return;
    const completed = interviews.filter(iv => iv.status === 'completed');
    (async () => {
      const readyIds: number[] = [];
      for (const iv of completed) {
        if (notifiedRef.current.has(iv.id) || viewedRef.current.has(iv.id)) continue;
        try {
          await apiFetch(`/api/v1/conversations/analysis/${iv.id}`);
          readyIds.push(iv.id);
        } catch {}
      }
      if (readyIds.length > 0) {
        const title = `${readyIds.length} rapor hazır`;
        const body = `Görüntülenmemiş ${readyIds.length} aday raporu hazır.`;
        const url = `/jobs/${interviews[0].job_id}/candidates`;
        tryShowNotification(title, body, url);
        readyIds.forEach(id => notifiedRef.current.add(id));
        if (typeof window !== 'undefined' && notifiedKey) {
          try { localStorage.setItem(notifiedKey, JSON.stringify(Array.from(notifiedRef.current))); } catch {}
        }
      }
    })();
  }, [interviews, candidates, dataLoaded, notifiedKey]);

  return (
    <DashboardContext.Provider
      value={{
        candidates,
        jobs,
        interviews,
        loading,
        dataLoaded,
        refreshData,
      }}
    >
      {children}
    </DashboardContext.Provider>
  );
}

export function useDashboard() {
  const context = useContext(DashboardContext);
  if (context === undefined) {
    throw new Error('useDashboard must be used within a DashboardProvider');
  }
  return context;
} 