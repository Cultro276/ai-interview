"use client";

import { create } from "zustand";
import { shallow } from "zustand/shallow";
import type { Candidate, Job, Interview } from "@/types/api";

type DashboardState = {
  candidates: Candidate[];
  jobs: Job[];
  interviews: Interview[];
  loading: boolean;
  dataLoaded: boolean;
  setCandidates: (c: Candidate[]) => void;
  setJobs: (j: Job[]) => void;
  setInterviews: (i: Interview[]) => void;
  setLoading: (v: boolean) => void;
  setDataLoaded: (v: boolean) => void;
  reset: () => void;
};

export const useDashboardStore = create<DashboardState>((set) => ({
  candidates: [],
  jobs: [],
  interviews: [],
  loading: true,
  dataLoaded: false,
  setCandidates: (candidates) => set({ candidates }),
  setJobs: (jobs) => set({ jobs }),
  setInterviews: (interviews) => set({ interviews }),
  setLoading: (v) => set({ loading: v }),
  setDataLoaded: (v) => set({ dataLoaded: v }),
  reset: () => set({ candidates: [], jobs: [], interviews: [], loading: true, dataLoaded: false }),
}));

export const shallowCompare = shallow;


