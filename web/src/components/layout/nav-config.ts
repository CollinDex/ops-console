import { Activity, Building2, LayoutDashboard, Users, type LucideIcon } from "lucide-react";

import type { Role } from "@/features/auth/types";

export type NavItem = {
  label: string;
  href: string;
  icon: LucideIcon;
  /** Omitted means every role. */
  roles?: Role[];
};

export const NAV_ITEMS: NavItem[] = [
  { label: "Overview", href: "/overview", icon: LayoutDashboard },
  { label: "Businesses", href: "/businesses", icon: Building2, roles: ["analyst", "ops_admin"] },
  { label: "Providers", href: "/providers", icon: Activity },
  { label: "Team", href: "/team", icon: Users, roles: ["analyst", "ops_admin"] },
];

export function navForRole(role: Role | undefined): NavItem[] {
  return NAV_ITEMS.filter((i) => !i.roles || (role !== undefined && i.roles.includes(role)));
}

export function titleForPath(pathname: string): string {
  return NAV_ITEMS.find((i) => pathname.startsWith(i.href))?.label ?? "CrediSure Ops Console";
}

export function isActive(pathname: string, href: string): boolean {
  return pathname.startsWith(href);
}
