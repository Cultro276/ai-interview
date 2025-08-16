"use client";
import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { apiFetch } from "@/lib/api";

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
  completed_at?: string;
  audio_url?: string;
  video_url?: string;
  overall_score?: number;
  communication_score?: number;
  technical_score?: number;
  cultural_fit_score?: number;
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

  const loadData = async () => {
    try {
      const [candidatesData, jobsData, interviewsData] = await Promise.all([
        apiFetch<Candidate[]>("/api/v1/candidates"),
        apiFetch<Job[]>("/api/v1/jobs"),
        apiFetch<Interview[]>("/api/v1/interviews"),
      ]);
      setCandidates(candidatesData || []);
      setJobs(jobsData || []);
      setInterviews(interviewsData || []);
      
      // Save to session storage as backup
      if (typeof window !== 'undefined') {
        sessionStorage.setItem('dashboardData', JSON.stringify({
          candidates: candidatesData || [],
          jobs: jobsData || [],
          interviews: interviewsData || []
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
            //
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
      
      // Try to load from session storage first
      if (typeof window !== 'undefined') {
        const savedData = sessionStorage.getItem('dashboardData');
        if (savedData) {
          try {
            const { candidates: savedCandidates, jobs: savedJobs, interviews: savedInterviews } = JSON.parse(savedData);
            setCandidates(savedCandidates || []);
            setJobs(savedJobs || []);
            setInterviews(savedInterviews || []);
            setDataLoaded(true);
            setLoading(false);
            return;
          } catch (e) {
            //
          }
        }
      }
      
      // If no saved data, load from API
      loadData();
    }
  }, [dataLoaded]);

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