"use client";

import { CircleX, RefreshCw } from "lucide-react";

import { ErrorState } from "@/components/data/states";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useAuth } from "@/features/auth/auth-provider";
import { useProvidersStatus } from "@/features/overview/queries";
import { useNow } from "@/lib/use-now";
import { cn } from "@/lib/utils";
import { ProviderCard } from "./provider-card";
import { USED_BY } from "./queries";

function updatedAgo(dataUpdatedAt: number, now: number): string {
  if (!dataUpdatedAt) return "Checking…";
  const s = Math.max(0, Math.round((now - dataUpdatedAt) / 1000));
  return s < 60 ? `Updated ${s} s ago` : `Updated ${Math.round(s / 60)} min ago`;
}

export function ProvidersPage() {
  const { hasRole } = useAuth();
  const query = useProvidersStatus();
  const now = useNow(1_000);
  const data = query.data;
  const down = data?.providers.filter((p) => p.status === "down") ?? [];

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold">Provider health</h2>
          <p className="text-muted-foreground text-sm">
            Live status of the verification APIs onboarding depends on
          </p>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-muted-foreground text-sm" aria-live="off">
            {updatedAgo(query.dataUpdatedAt, now)}
          </span>
          <Button
            variant="outline"
            aria-label="Refresh provider status"
            onClick={() => void query.refetch()}
            disabled={query.isFetching}
            className="min-h-10 sm:min-h-8"
          >
            <RefreshCw className={cn(query.isFetching && "animate-spin")} aria-hidden="true" />
            Refresh
          </Button>
        </div>
      </div>

      {data && (
        <p className="text-sm font-medium tabular-nums">
          {data.summary.up} up · {data.summary.slow} slow · {data.summary.down} down
        </p>
      )}

      {down.length > 0 && (
        <div
          role="alert"
          className="border-danger/40 bg-danger/10 text-danger flex items-start gap-2 rounded-lg border p-3 text-sm"
        >
          <CircleX className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
          <div className="space-y-1">
            {down.map((p) => (
              <p key={p.name}>
                <span className="font-semibold">{p.label} is down.</span> {USED_BY[p.name]}s will
                fail until it recovers. This is a provider problem, not an applicant problem.
              </p>
            ))}
          </div>
        </div>
      )}

      {data ? (
        <div className="grid gap-4 md:grid-cols-2">
          {data.providers.map((p) => (
            <ProviderCard key={p.name} provider={p} isAdmin={hasRole("ops_admin")} />
          ))}
        </div>
      ) : query.isError ? (
        <ErrorState
          error={query.error}
          retrying={query.isFetching}
          onRetry={() => void query.refetch()}
        />
      ) : (
        <div className="grid gap-4 md:grid-cols-2" aria-busy="true">
          {Array.from({ length: 4 }, (_, i) => (
            <Skeleton key={i} className="h-72 w-full rounded-xl" />
          ))}
        </div>
      )}
    </div>
  );
}
