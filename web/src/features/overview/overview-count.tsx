"use client";

import { useQuery } from "@tanstack/react-query";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api-client";
import type { components } from "@/lib/api-types";
import { formatNumber } from "@/lib/format";

type OverviewStats = components["schemas"]["OverviewStats"];

export function OverviewCount() {
  const { data, isPending, isError } = useQuery({
    queryKey: ["stats", "overview"],
    queryFn: ({ signal }) => api<OverviewStats>("/stats/overview", { signal }),
  });

  return (
    <Card className="max-w-md">
      <CardHeader>
        <CardDescription>Total businesses</CardDescription>
        <CardTitle className="text-3xl tabular-nums">
          {isPending ? (
            <Skeleton className="h-9 w-24" />
          ) : isError ? (
            <span className="text-muted-foreground text-base font-normal">Unavailable</span>
          ) : (
            <span className="font-mono">{formatNumber(data.cards.total_businesses)}</span>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent className="text-muted-foreground text-sm">
        Full overview arrives in Phase 6.
      </CardContent>
    </Card>
  );
}
