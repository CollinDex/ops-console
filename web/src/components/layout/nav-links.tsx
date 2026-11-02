"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { useAuth } from "@/features/auth/auth-provider";
import { cn } from "@/lib/utils";
import { isActive, navForRole } from "./nav-config";

export function NavLinks({ className }: { className?: string }) {
  const pathname = usePathname();
  const { user } = useAuth();
  return (
    <nav aria-label="Main" className={className}>
      <ul className="space-y-1">
        {navForRole(user?.role).map((item) => {
          const active = isActive(pathname, item.href);
          return (
            <li key={item.href}>
              <Link
                href={item.href}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "focus-visible:ring-ring/60 flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors outline-none focus-visible:ring-2",
                  active
                    ? "bg-sidebar-accent text-sidebar-accent-foreground"
                    : "text-muted-foreground hover:bg-sidebar-accent/60 hover:text-foreground",
                )}
              >
                <item.icon className="size-4" aria-hidden="true" />
                {item.label}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
