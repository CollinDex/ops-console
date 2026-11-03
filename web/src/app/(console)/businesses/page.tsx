"use client";

import { RoleGate } from "@/components/layout/role-gate";
import { BusinessesPage } from "@/features/businesses/businesses-page";

export default function Page() {
  return (
    <RoleGate roles={["analyst", "ops_admin"]} feature="Businesses">
      <BusinessesPage />
    </RoleGate>
  );
}
