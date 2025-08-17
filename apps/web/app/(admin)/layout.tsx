"use client";
import { AuthProvider } from "@/context/AuthContext";
import { DashboardProvider } from "@/context/DashboardContext";
import Link from "next/link";
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
        <div className="min-h-screen bg-gray-50">
          {!isLogin && (
            <nav className="bg-white shadow-sm border-b">
              <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div className="flex justify-between h-16">
                  <div className="flex items-center">
                    <h1 className="text-xl font-bold text-gray-900">Hirevision Admin</h1>
                  </div>
                  <div className="flex items-center space-x-4">
                    <Link href="/dashboard" className="text-gray-600 hover:text-gray-900 px-3 py-2 rounded-md text-sm font-medium">
                      Dashboard
                    </Link>
                    {/* Removed top-level Candidates page; candidate management lives under each Job */}
                    <Link href="/jobs" className="text-gray-600 hover:text-gray-900 px-3 py-2 rounded-md text-sm font-medium">
                      Jobs
                    </Link>
                    <Link href="/interviews" className="text-gray-600 hover:text-gray-900 px-3 py-2 rounded-md text-sm font-medium">
                      Interviews
                    </Link>
                  </div>
                </div>
              </div>
            </nav>
          )}
          <main className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
            {isLogin ? (
              <div>{children}</div>
            ) : (
              <div className="bg-white rounded-lg shadow">
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