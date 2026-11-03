import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { api } from "@/lib/api-client";
import type { components } from "@/lib/api-types";

export type ProviderStatus = components["schemas"]["ProviderStatusOut"];
export type ProviderName = ProviderStatus["name"];
export type ProviderMode = ProviderStatus["mode"];
export type Incident = components["schemas"]["IncidentOut"];

export function useProviderIncidents(name: ProviderName, enabled: boolean) {
  return useQuery({
    queryKey: ["providers", name, "incidents"],
    queryFn: ({ signal }) => api<Incident[]>(`/providers/${name}/incidents`, { signal }),
    enabled,
    meta: { silent: true },
  });
}

const MODE_LABEL: Record<ProviderMode, string> = { up: "Up", slow: "Slow", down: "Down" };

export function useSimulateProvider(name: ProviderName, label: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (mode: ProviderMode) =>
      api<ProviderStatus>(`/providers/${name}/simulate`, { method: "POST", body: { mode } }),
    onSuccess: (_res, mode) => toast.success(`${label} set to ${MODE_LABEL[mode]}`),
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: ["providers"] });
      void queryClient.invalidateQueries({ queryKey: ["health"] });
    },
  });
}

/** The check that depends on each provider. */
export const USED_BY: Record<ProviderName, string> = {
  bvn: "BVN check",
  cac: "CAC check",
  tin: "Tax ID check",
  open_banking: "Bank link check",
};
