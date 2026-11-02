"use client";

import { useAuth } from "@/features/auth/auth-provider";
import type { Role } from "@/features/auth/types";
import { Forbidden } from "./forbidden";

export function RoleGate({
  roles,
  feature,
  children,
}: {
  roles: Role[];
  feature: string;
  children: React.ReactNode;
}) {
  const { hasRole } = useAuth();
  if (!hasRole(...roles)) return <Forbidden feature={feature} />;
  return <>{children}</>;
}
