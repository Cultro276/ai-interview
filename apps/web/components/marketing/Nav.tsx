"use client";
import Link from "next/link";
import { Button } from "@/components/ui/Button";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { Moon, Sun } from "lucide-react";
import { useTheme } from "next-themes";

export function MarketingNav({ active }: { active?: "home" | "pricing" | "contact" | "blog" }) {
  const { theme, setTheme } = useTheme() as any;
  return (
    <nav className="flex items-center justify-between px-6 py-4 bg-white shadow-sm">
      <div className="text-2xl font-bold text-gray-900">
        <Link href="/">Hirevision</Link>
      </div>
      <div className="hidden md:flex space-x-8">
        <Link href="/" className={`${active === "home" ? "text-blue-600 font-semibold" : "text-gray-600 hover:text-gray-900"}`}>Features</Link>
        <Link href="/pricing" className={`${active === "pricing" ? "text-blue-600 font-semibold" : "text-gray-600 hover:text-gray-900"}`}>Pricing</Link>
        <Link href="/contact" className={`${active === "contact" ? "text-blue-600 font-semibold" : "text-gray-600 hover:text-gray-900"}`}>Contact</Link>
        <Link href="/blog" className={`${active === "blog" ? "text-blue-600 font-semibold" : "text-gray-600 hover:text-gray-900"}`}>Blog</Link>
      </div>
      <div className="flex space-x-3 items-center">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button aria-label="Toggle theme" className="p-2 rounded-md hover:bg-neutral-100">
              {theme === "dark" ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={() => setTheme("light")}>Light</DropdownMenuItem>
            <DropdownMenuItem onClick={() => setTheme("dark")}>Dark</DropdownMenuItem>
            <DropdownMenuItem onClick={() => setTheme("system")}>System</DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
        <Link href="/login" className="px-4 py-2 text-blue-600 border border-blue-600 rounded-lg hover:bg-blue-50">
          Login
        </Link>
        <Button variant="primary">Request Demo</Button>
      </div>
    </nav>
  );
}


