import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api-client";
import type { components } from "@/lib/api-types";

export type OverviewStats = components["schemas"]["OverviewStats"];
export type ProvidersStatus = components["schemas"]["ProvidersStatusOut"];

// Blocks render their own ErrorState, so these queries are silent (no duplicate toast).
export function useOverviewStats() {
  return useQuery({
    queryKey: ["stats", "overview"],
    queryFn: ({ signal }) => api<OverviewStats>("/stats/overview", { signal }),
    refetchInterval: 60_000,
    meta: { silent: true },
  });
}

export function useProvidersStatus() {
  return useQuery({
    queryKey: ["providers", "status"],
    queryFn: ({ signal }) => api<ProvidersStatus>("/providers/status", { signal }),
    refetchInterval: 15_000,
    meta: { silent: true, background: true },
  });
}
