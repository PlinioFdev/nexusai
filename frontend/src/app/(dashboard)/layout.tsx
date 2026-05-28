"use client";

import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import Link from "next/link";
import { FileText, MessageSquare, LogOut } from "lucide-react";
import { isAuthenticated, clearTokens, getStoredUser } from "@/lib/auth";
import type { UserResponse } from "@/lib/types";

const NAV_ITEMS = [
  { href: "/documents", label: "Documentos", icon: FileText },
  { href: "/chat", label: "Chat", icon: MessageSquare },
];

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const [user, setUser] = useState<UserResponse | null>(null);
  const [isChecking, setIsChecking] = useState(true);

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace("/login");
      setIsChecking(false);
      return;
    }
    setUser(getStoredUser());
    setIsChecking(false);
  }, [router]);

  function handleLogout() {
    clearTokens();
    router.replace("/login");
  }

  if (isChecking) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <span className="text-sm text-gray-400">Carregando...</span>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen flex-col">
      <header className="border-b border-gray-200 bg-white px-6 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-6">
            <span className="text-base font-bold text-gray-900">NexusAI</span>
            <nav className="flex items-center gap-1">
              {NAV_ITEMS.map(({ href, label, icon: Icon }) => (
                <Link
                  key={href}
                  href={href}
                  className={[
                    "flex items-center gap-2 rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
                    pathname === href
                      ? "bg-indigo-50 text-indigo-700"
                      : "text-gray-600 hover:bg-gray-100",
                  ].join(" ")}
                >
                  <Icon className="h-4 w-4" />
                  {label}
                </Link>
              ))}
            </nav>
          </div>

          <div className="flex items-center gap-3">
            {user && (
              <span className="text-sm text-gray-500">{user.email}</span>
            )}
            <button
              onClick={handleLogout}
              className="flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100 transition-colors"
            >
              <LogOut className="h-4 w-4" />
              Sair
            </button>
          </div>
        </div>
      </header>

      <main className="flex flex-1 flex-col">{children}</main>
    </div>
  );
}
