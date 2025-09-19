"use client";
import { useCallback, useMemo, useRef, useState } from "react";

export function useInterviewFlow() {
  const [status, setStatus] = useState<
    | "loading"
    | "invalid"
    | "consent"
    | "permissions"
    | "permissionsDenied"
    | "test"
    | "intro"
    | "interview"
    | "finished"
  >("loading");
  const [question, setQuestion] = useState<string | null>(null);
  const [history, setHistory] = useState<{ role: "assistant" | "user"; text: string }[]>([]);
  const askedCount = useMemo(() => history.filter(t => t.role === "assistant").length, [history]);

  const sanitizeQuestion = useCallback((q: string) => (q || "").replace(/\bFINISHED\b/gi, "").trim(), []);

  return {
    status,
    setStatus,
    question,
    setQuestion,
    history,
    setHistory,
    askedCount,
    sanitizeQuestion,
  } as const;
}
