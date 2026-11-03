"use client";

import Link from "next/link";

import { Skeleton } from "@/components/ui/skeleton";
import { useAuth } from "@/features/auth/auth-provider";
import { formatNumber } from "@/lib/format";
import { Block } from "./block";
import { useOverviewStats } from "./queries";

export function Funnel() {
  const query = useOverviewStats();
  const { hasRole } = useAuth();
  const canDrill = hasRole("analyst", "ops_admin");

  return (
    <Block
      title="Onboarding funnel"
      description="Where businesses are right now, in funnel order."
      query={query}
      className="lg:col-span-2"
      skeleton={
        <div className="space-y-3">
          {Array.from({ length: 5 }, (_, i) => (
            <Skeleton key={i} className="h-9 w-full" />
          ))}
        </div>
      }
    >
      {(data) => {
        const max = Math.max(1, ...data.funnel.map((f) => f.count));
        const total = data.cards.total_businesses;
        return (
          <ol className="space-y-2">
            {data.funnel.map((step) => {
              const pct = total ? Math.round((step.count / total) * 100) : 0;
              const inner = (
                <>
                  <div className="mb-1 flex items-baseline justify-between gap-2 text-sm">
                    <span className="font-medium">{step.label}</span>
                    <span className="text-muted-foreground tabular-nums">
                      <span className="text-foreground font-mono font-medium">
                        {formatNumber(step.count)}
                      </span>{" "}
                      · {pct}%
                    </span>
                  </div>
                  <div className="bg-muted h-2.5 overflow-hidden rounded-full" aria-hidden="true">
                    <div
                      className="bg-primary h-full rounded-full"
                      style={{ width: `${(step.count / max) * 100}%` }}
                    />
                  </div>
                </>
              );
              return (
                <li key={step.stage}>
                  {canDrill ? (
                    <Link
                      href={`/businesses?stage=${step.stage}`}
                      className="hover:bg-muted/50 focus-visible:ring-ring/50 -mx-2 block rounded-md px-2 py-1.5 outline-none focus-visible:ring-2"
                    >
                      {inner}
                    </Link>
                  ) : (
                    <div className="py-1.5">{inner}</div>
                  )}
                </li>
              );
            })}
          </ol>
        );
      }}
    </Block>
  );
}
