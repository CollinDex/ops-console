"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";

import { AppShell, ShellSkeleton } from "@/components/layout/app-shell";
import { useAuth } from "@/features/auth/auth-provider";

export default function ConsoleLayout({ children }: { children: React.ReactNode }) {
  const { status, redirecting } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    // logout() already navigates (with its own ?reason=), so don't override it here.
    if (status === "anonymous" && !redirecting) {
      router.replace("/login?next=" + encodeURIComponent(pathname));
    }
  }, [status, redirecting, pathname, router]);

  if (status !== "authenticated") return <ShellSkeleton />;
  return <AppShell>{children}</AppShell>;
}
