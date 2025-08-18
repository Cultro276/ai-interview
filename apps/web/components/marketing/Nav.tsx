"use client";
import Link from "next/link";
import { Button } from "@/components/ui/Button";
import { ThemeToggle } from "../theme/ThemeToggle";

export function MarketingNav({ active }: { active?: "home" | "pricing" | "contact" | "blog" }) {
  return (
    <nav className="flex items-center justify-between px-6 py-4 bg-white dark:bg-neutral-900 shadow-sm">
      <div className="text-2xl font-bold text-gray-900">
        <Link href="/">Hirevision</Link>
      </div>
      <div className="hidden md:flex space-x-8">
        <Link href="/" className={`${active === "home" ? "text-brand-700 font-semibold" : "text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white"}`}>Özellikler</Link>
        <Link href="/pricing" className={`${active === "pricing" ? "text-brand-700 font-semibold" : "text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white"}`}>Fiyatlandırma</Link>
        <Link href="/contact" className={`${active === "contact" ? "text-brand-700 font-semibold" : "text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white"}`}>İletişim</Link>
        <Link href="/blog" className={`${active === "blog" ? "text-brand-700 font-semibold" : "text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white"}`}>Blog</Link>
      </div>
      <div className="flex space-x-3 items-center">
        <ThemeToggle />
        <Link href="/login" className="px-4 py-2 text-brand-700 border border-brand-700 rounded-lg hover:bg-brand-25 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500">
          Login
        </Link>
        <Button variant="primary">Request Demo</Button>
      </div>
    </nav>
  );
}


