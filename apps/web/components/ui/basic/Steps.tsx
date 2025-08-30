import React from "react";
import { cn } from "@/components/ui/utils/cn";

export function Steps({
  steps,
  current,
  className,
}: {
  steps: string[];
  current: number; // 0-based index
  className?: string;
}) {
  return (
    <ol className={cn("flex items-center justify-center gap-4", className)}>
      {steps.map((label, i) => {
        const state = i < current ? "done" : i === current ? "current" : "todo";
        return (
          <li key={label} className="flex items-center gap-2">
            <span
              className={cn(
                "w-6 h-6 rounded-full grid place-items-center text-xs font-semibold",
                state === "done" && "bg-green-600 text-white",
                state === "current" && "bg-blue-600 text-white",
                state === "todo" && "bg-gray-200 text-gray-600",
              )}
            >
              {i + 1}
            </span>
            <span className={cn("text-sm", state === "todo" && "text-gray-500")}>{label}</span>
            {i < steps.length - 1 && <span className="w-8 h-px bg-gray-300 mx-2" />}
          </li>
        );
      })}
    </ol>
  );
}

