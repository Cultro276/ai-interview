"use client";

import { create } from "zustand";

type DeltaEvent = { type: string; payload: any };

type RealtimeState = {
  events: DeltaEvent[];
  push: (e: DeltaEvent) => void;
  clear: () => void;
};

export const useRealtimeStore = create<RealtimeState>((set, get) => ({
  events: [],
  push: (e) => set({ events: [...get().events, e] }),
  clear: () => set({ events: [] }),
}));


