"use client";

import { Funnel } from "./funnel";
import { NeedsAttention } from "./needs-attention";
import { ProviderSummary } from "./provider-summary";
import { SignupsChart } from "./signups-chart";
import { StatCards } from "./stat-cards";

export function OverviewPage() {
  return (
    <div className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCards />
      </div>
      <div className="grid gap-4 lg:grid-cols-3">
        <Funnel />
        <ProviderSummary />
        <NeedsAttention />
        <SignupsChart />
      </div>
    </div>
  );
}
