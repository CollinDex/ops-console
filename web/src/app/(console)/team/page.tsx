"use client";

import { RoleGate } from "@/components/layout/role-gate";
import { StaffPage } from "@/features/staff/staff-page";

export default function Page() {
  return (
    <RoleGate roles={["analyst", "ops_admin"]} feature="Team">
      <StaffPage />
    </RoleGate>
  );
}
