"use client";
import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
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

  const loadData = async () => {
    try {
      // Skip API calls if there is no auth token (e.g., on /login)
      const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
      if (!token) {
        setDataLoaded(true);
        setLoading(false);
        return;
      }
      const [candidatesRes, jobsRes, interviewsRes] = await Promise.allSettled([
        apiFetch<Candidate[]>("/api/v1/candidates/"),
        apiFetch<Job[]>("/api/v1/jobs/"),
        apiFetch<Interview[]>("/api/v1/interviews/"),
      ]);

      const nextCandidates = candidatesRes.status === "fulfilled" ? (candidatesRes.value || []) : candidates;
      const nextJobs = jobsRes.status === "fulfilled" ? (jobsRes.value || []) : jobs;
      const nextInterviews = interviewsRes.status === "fulfilled" ? (interviewsRes.value || []) : interviews;

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