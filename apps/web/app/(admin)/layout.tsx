"use client";
import { AuthProvider, useAuth } from "@/context/AuthContext";
import { DashboardProvider } from "@/context/DashboardContext";
import Link from "next/link";
import { ThemeToggle } from "@/components/theme/ThemeToggle";
import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  // Simple client-side guard for admin routes
  const router = useRouter();
  const pathname = usePathname();
  const isLogin = pathname === "/login";
  const [allowed, setAllowed] = useState<boolean>(isLogin);

  useEffect(() => {
    // Allow the login page to render without token
    if (isLogin) {
      setAllowed(true);
      return;
    }
    const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
    if (!token) {
      router.replace("/login");
      setAllowed(false);
      return;
    }
    setAllowed(true);
  }, [router, isLogin]);

  if (!allowed) {
    return null;
  }
  return (
    <AuthProvider>
      <DashboardProvider>
        <div className="min-h-screen bg-gray-50 dark:bg-neutral-950">
          {!isLogin && (
            <nav className="bg-white dark:bg-neutral-900 shadow-sm border-b border-neutral-200 dark:border-neutral-800">
              <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div className="flex justify-between h-16">
                  <div className="flex items-center">
                    <h1 className="text-xl font-bold text-gray-900 dark:text-neutral-100">Hirevision Admin</h1>
                  </div>
                  <div className="flex items-center space-x-4">
                    <Link href="/dashboard" className="text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white px-3 py-2 rounded-md text-sm font-medium">
                      Dashboard
                    </Link>
                    {/* Removed top-level Candidates page; candidate management lives under each Job */}
                    <Link href="/jobs" className="text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white px-3 py-2 rounded-md text-sm font-medium">
                      Jobs
                    </Link>
                    <TeamLink />
                    {/* Founders link is fully hidden to all users; remove from navigation. */}
                    {/* Interviews page removed; all actions under each Job's candidates */}
                    <ThemeToggle />
                  </div>
                </div>
              </div>
            </nav>
          )}
          <main className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
            {isLogin ? (
              <div>{children}</div>
            ) : (
              <div className="bg-white dark:bg-neutral-900 rounded-lg shadow border border-neutral-200 dark:border-neutral-800">
                <div className="p-6">
                  {children}
                </div>
              </div>
            )}
          </main>
        </div>
      </DashboardProvider>
    </AuthProvider>
  );
} 

function TeamLink() {
  try {
    const { user } = useAuth();
    if (!user) return null;
    if (user.is_admin || user.can_manage_members) {
      return (
        <Link href="/team" className="text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white px-3 py-2 rounded-md text-sm font-medium">
          Team
        </Link>
      );
    }
  } catch {}
  return null;
}

function InternalLink() {
  try {
    const { user } = useAuth();
    if (!user) return null;
    // Platform admins (founders) have is_superuser in backend; not present in user payload by default.
    // As a simple client gate, hide link unless the email is a known founder alias.
    // Real enforcement is on the API via platform_admin_required.
    const founderEmails = ["admin@example.com", "owner2@example.com"]; // adjust as needed for local dev
    if (founderEmails.includes(user.email)) {
      return (
        <Link href="/internal" className="text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white px-3 py-2 rounded-md text-sm font-medium">
          Founders
        </Link>
      );
    }
  } catch {}
  return null;
}