"use client";
import { useToast } from "@/context/ToastContext";

export function Toaster() {
  const { toasts, remove } = useToast();
  return (
    <div className="fixed top-4 right-4 space-y-3 z-50">
      {toasts.map((t) => (
        <div
          key={t.id}
          className={`min-w-[280px] max-w-sm px-4 py-3 rounded-md shadow border text-sm flex items-start gap-2 bg-white ${
            t.type === "success" ? "border-emerald-300" : t.type === "error" ? "border-rose-300" : "border-slate-300"
          }`}
        >
          <div className="mt-0.5">
            {t.type === "success" ? "✅" : t.type === "error" ? "⚠️" : "ℹ️"}
          </div>
          <div className="flex-1 text-slate-800">{t.text}</div>
          <button className="text-slate-500 hover:text-slate-700" onClick={() => remove(t.id)}>✕</button>
        </div>
      ))}
    </div>
  );
}


