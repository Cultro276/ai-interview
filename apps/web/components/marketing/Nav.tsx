"use client";
import Link from "next/link";
import { Button } from "@/components/ui";
import { ThemeToggle } from "../theme/ThemeToggle";
import { productName } from "@/lib/brand";
import Image from "next/image";

export function MarketingNav({ active }: { active?: "home" | "contact" }) {
  return (
    <nav className="flex items-center justify-between px-6 py-4 bg-white dark:bg-neutral-900 shadow-sm">
      <div className="flex items-center gap-2 text-2xl font-bold text-gray-900">
        <Link href="/" className="flex items-center gap-2">
          <Image src="/logo.png" alt="RecruiterAI logo" width={28} height={28} />
          <span>{productName}</span>
        </Link>
      </div>
      <div className="hidden md:flex space-x-8">
        <Link href="/solutions" className={`${active === "home" ? "text-brand-700 font-semibold" : "text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white"}`}>Çözümler</Link>
        <Link href="/how-it-works" className={`text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white`}>Nasıl Çalışır</Link>
        <Link href="/roi" className={`text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white`}>ROI</Link>
        <Link href="/contact" className={`${active === "contact" ? "text-brand-700 font-semibold" : "text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white"}`}>İletişim</Link>
      </div>
      <div className="flex space-x-3 items-center">
        <ThemeToggle />
        <Link href="/login" className="px-4 py-2 text-brand-700 border border-brand-700 rounded-lg hover:bg-brand-25 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500">
          Giriş Yap
        </Link>
        <Link href="/contact?utm_source=site&utm_medium=cta&utm_campaign=nav">
          <Button variant="primary">Demo Talep Et</Button>
        </Link>
      </div>
    </nav>
  );
}


