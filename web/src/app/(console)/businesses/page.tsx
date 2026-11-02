"use client";

import { RoleGate } from "@/components/layout/role-gate";

export default function BusinessesPage() {
  return (
    <RoleGate roles={["analyst", "ops_admin"]} feature="Businesses">
      <p className="text-muted-foreground text-sm">Businesses arrives in a later phase.</p>
    </RoleGate>
  );
}
