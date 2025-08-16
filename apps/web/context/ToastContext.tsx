"use client";
import React, { createContext, useContext, useMemo, useState, useCallback, ReactNode, useEffect } from "react";

export type ToastType = "success" | "error" | "info";

export interface ToastMessage {
  id: string;
  type: ToastType;
  text: string;
}

interface ToastContextValue {
  toasts: ToastMessage[];
  show: (type: ToastType, text: string) => void;
  success: (text: string) => void;
  error: (text: string) => void;
  info: (text: string) => void;
  remove: (id: string) => void;
}

const ToastContext = createContext<ToastContextValue | undefined>(undefined);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const remove = useCallback((id: string) => {
    setToasts((t) => t.filter((x) => x.id !== id));
  }, []);

  const show = useCallback((type: ToastType, text: string) => {
    const id = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
    const msg: ToastMessage = { id, type, text };
    setToasts((t) => [...t, msg]);
    // Auto-dismiss after 4s
    window.setTimeout(() => remove(id), 4000);
  }, [remove]);

  const value = useMemo<ToastContextValue>(() => ({
    toasts,
    show,
    success: (text: string) => show("success", text),
    error: (text: string) => show("error", text),
    info: (text: string) => show("info", text),
    remove,
  }), [toasts, show, remove]);

  return <ToastContext.Provider value={value}>{children}</ToastContext.Provider>;
}

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used within ToastProvider");
  return ctx;
}


