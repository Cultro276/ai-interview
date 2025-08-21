"use client";
import { useEffect } from "react";

export default function InterviewsPage() {
  useEffect(() => {
    if (typeof window !== "undefined") {
      window.location.replace("/jobs");
    }
  }, []);
  return <div>Interviews page deprecated. Redirecting to Jobs…</div>;
} 