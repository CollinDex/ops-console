"use client";

import { usePathname } from "next/navigation";

import { HealthDot } from "./health-dot";
import { MobileNav } from "./mobile-nav";
import { titleForPath } from "./nav-config";
import { ThemeToggle } from "./theme-toggle";
import { UserMenu } from "./user-menu";

export function Header() {
  const pathname = usePathname();
  return (
    <header className="bg-background/90 sticky top-0 z-30 flex h-14 items-center gap-2 border-b px-4 backdrop-blur">
      <MobileNav />
      <h1 className="truncate text-base font-semibold">{titleForPath(pathname)}</h1>
      <div className="ml-auto flex items-center gap-1">
        <HealthDot />
        <ThemeToggle />
        <UserMenu />
      </div>
    </header>
  );
}
