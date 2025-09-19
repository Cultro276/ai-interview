"use client";
import React, { createContext, useContext, useState, useEffect, useRef, ReactNode } from 'react';
import { apiFetch } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import type { Candidate, Job, Interview } from "@/types/api";
import { useQuery } from "@tanstack/react-query";
import { useDashboardStore } from "@/lib/hooks/useDashboardStore";


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

  // Zustand store setters for hydration (avoid Context-driven re-renders in consumers)
  const setStoreCandidates = useDashboardStore(s => s.setCandidates);
  const setStoreJobs = useDashboardStore(s => s.setJobs);
  const setStoreInterviews = useDashboardStore(s => s.setInterviews);
  const setStoreLoading = useDashboardStore(s => s.setLoading);
  const setStoreDataLoaded = useDashboardStore(s => s.setDataLoaded);
  const resetStore = useDashboardStore(s => s.reset);

  const cacheKey = typeof window !== 'undefined' && user ? `dashboardData:${user.id}` : null;
  const notifiedKey = typeof window !== 'undefined' && user ? `notifiedAnalyses:${user.id}` : null;
  const viewedKey = typeof window !== 'undefined' && user ? `viewedAnalyses:${user.id}` : null;
  const notifiedRef = useRef<Set<number>>(new Set());
  const viewedRef = useRef<Set<number>>(new Set());
  const [notificationStateLoaded, setNotificationStateLoaded] = useState(false);

  const canLoad = typeof window !== 'undefined' ? Boolean(localStorage.getItem('token')) : false;

  const {
    data: candData,
    isFetching: fetchingCand,
    refetch: refetchCandidates,
  } = useQuery({
    queryKey: ["candidates"],
    queryFn: () => apiFetch<Candidate[]>("/api/v1/candidates/"),
    enabled: false,
    staleTime: 30_000,
  });
  const {
    data: jobsData,
    isFetching: fetchingJobs,
    refetch: refetchJobs,
  } = useQuery({
    queryKey: ["jobs"],
    queryFn: () => apiFetch<Job[]>("/api/v1/jobs/"),
    enabled: false,
    staleTime: 30_000,
  });
  const {
    data: ivData,
    isFetching: fetchingIv,
    refetch: refetchInterviews,
  } = useQuery({
    queryKey: ["interviews"],
    queryFn: () => apiFetch<Interview[]>("/api/v1/interviews/"),
    enabled: false,
    staleTime: 30_000,
  });

  const loadData = async () => {
    try {
      // Skip API calls if there is no auth token (e.g., on /login)
      const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
      if (!token) {
        console.warn("No authentication token found - skipping API calls");
        setDataLoaded(true);
        setLoading(false);
        setStoreDataLoaded(true);
        setStoreLoading(false);
        return;
      }
      // Use React Query to fetch fresh data
      const [rc, rj, ri] = await Promise.allSettled([
        refetchCandidates(),
        refetchJobs(),
        refetchInterviews(),
      ]);

      const nextCandidates = rc.status === "fulfilled" ? (rc.value.data || []) : (candData || []);
      const nextJobs = rj.status === "fulfilled" ? (rj.value.data || []) : (jobsData || []);
      const nextInterviews = ri.status === "fulfilled" ? (ri.value.data || []) : (ivData || []);

      setCandidates(nextCandidates);
      setJobs(nextJobs);
      setInterviews(nextInterviews);
      // Hydrate Zustand store (single state source for consumers)
      setStoreCandidates(nextCandidates);
      setStoreJobs(nextJobs);
      setStoreInterviews(nextInterviews);

      // Save per-user backup cache
      if (typeof window !== 'undefined' && cacheKey) {
        sessionStorage.setItem(cacheKey, JSON.stringify({
          candidates: nextCandidates,
          jobs: nextJobs,
          interviews: nextInterviews,
        }));
      }

      setDataLoaded(true);
      setStoreDataLoaded(true);
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
            setStoreCandidates(savedCandidates || []);
            setStoreJobs(savedJobs || []);
            setStoreInterviews(savedInterviews || []);
          } catch (e) {
            // ignore JSON parse error
          }
        }
      }

      setDataLoaded(true);
      setStoreDataLoaded(true);
    } finally {
      setLoading(false);
      setStoreLoading(false);
    }
  };

  const refreshData = async () => {
    setLoading(true);
    await loadData();
  };

  useEffect(() => {
    if (!dataLoaded) {
      // If no token, don't attempt initial load
      if (!canLoad) {
        setDataLoaded(true);
        setLoading(false);
        setStoreDataLoaded(true);
        setStoreLoading(false);
        return;
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
            setStoreCandidates(savedCandidates || []);
            setStoreJobs(savedJobs || []);
            setStoreInterviews(savedInterviews || []);
            // Do not return early; kick off a background refresh to avoid stale cache
            setDataLoaded(true);
            setLoading(false);
            setStoreDataLoaded(true);
            setStoreLoading(false);
            // Reconcile with server in background
            loadData();
            return;
          } catch (e) {
            // ignore
          }
        }
      }
      // If no saved data, load from API via React Query
      loadData();
    }
  }, [dataLoaded, cacheKey, canLoad]);

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
    resetStore();
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
    // Mark as ready so notification effect won't run before restoration completes
    setNotificationStateLoaded(true);
  }, [notifiedKey, viewedKey]);

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
    if (!dataLoaded || !interviews?.length || !notificationStateLoaded) return;
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
  }, [interviews, candidates, dataLoaded, notifiedKey, notificationStateLoaded]);

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