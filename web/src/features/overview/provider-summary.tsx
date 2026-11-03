"use client";

import Link from "next/link";

import { ProviderStatusBadge } from "@/components/data/status-badges";
import { Skeleton } from "@/components/ui/skeleton";
import { useNow } from "@/lib/use-now";
import { Block } from "./block";
import { useProvidersStatus } from "./queries";

function updatedAgo(dataUpdatedAt: number, now: number): string {
  if (!dataUpdatedAt) return "";
  const s = Math.max(0, Math.round((now - dataUpdatedAt) / 1000));
  return s < 60 ? `Updated ${s} s ago` : `Updated ${Math.round(s / 60)} min ago`;
}

export function ProviderSummary() {
  const query = useProvidersStatus();
  const now = useNow(5_000);
  return (
    <Block
      title="Provider health"
      description={updatedAgo(query.dataUpdatedAt, now) || "Verification providers"}
      query={query}
      skeleton={
        <div className="space-y-3">
          {Array.from({ length: 4 }, (_, i) => (
            <Skeleton key={i} className="h-7 w-full" />
          ))}
        </div>
      }
    >
      {(data) => (
        <div className="space-y-3">
          <ul className="divide-y">
            {data.providers.map((p) => (
              <li key={p.name} className="flex items-center justify-between gap-2 py-2 text-sm">
                <span className="font-medium">{p.label}</span>
                <span className="flex items-center gap-2">
                  <span className="text-muted-foreground font-mono text-xs tabular-nums">
                    {p.latency_ms === null ? "—" : `${p.latency_ms} ms`}
                  </span>
                  <ProviderStatusBadge status={p.status} />
                </span>
              </li>
            ))}
          </ul>
          <Link
            href="/providers"
            className="text-primary inline-flex items-center text-sm font-medium hover:underline max-sm:min-h-10"
          >
            View providers
          </Link>
        </div>
      )}
    </Block>
  );
}
