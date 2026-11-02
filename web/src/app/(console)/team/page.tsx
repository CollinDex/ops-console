"use client";

import { RoleGate } from "@/components/layout/role-gate";

export default function TeamPage() {
  return (
    <RoleGate roles={["analyst", "ops_admin"]} feature="Team">
      <p className="text-muted-foreground text-sm">Team arrives in a later phase.</p>
    </RoleGate>
  );
}
