import React from "react";
import { cn } from "@/components/ui/cn";

type BadgeVariant = "default" | "success" | "warning" | "info" | "neutral";

const styles: Record<BadgeVariant, string> = {
  default: "bg-brand-100 text-brand-800 ring-1 ring-inset ring-brand-200",
  success: "bg-green-100 text-green-800 ring-1 ring-inset ring-green-200",
  warning: "bg-yellow-100 text-yellow-800 ring-1 ring-inset ring-yellow-200",
  info: "bg-blue-100 text-blue-800 ring-1 ring-inset ring-blue-200",
  neutral: "bg-gray-100 text-gray-800 ring-1 ring-inset ring-gray-200",
};

export function Badge({
  className,
  variant = "default",
  children,
}: {
  className?: string;
  variant?: BadgeVariant;
  children: React.ReactNode;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center px-2 py-1 rounded-full text-xs font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500",
        styles[variant],
        className,
      )}
    >
      {children}
    </span>
  );
}


