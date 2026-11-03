import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";

import { CHECK_LABEL, type CheckType } from "@/components/data/status-badges";
import { api, ApiError } from "@/lib/api-client";
import type { components } from "@/lib/api-types";
import { apiParamsToQuery, type BusinessApiParams } from "./filters";

export type FilterMeta = components["schemas"]["FilterMeta"];
export type BusinessPage = components["schemas"]["Page_BusinessListItem_"];
export type BusinessListItem = components["schemas"]["BusinessListItem"];
export type BusinessDetail = components["schemas"]["BusinessDetail"];
export type AuditEntry = components["schemas"]["AuditEntry"];
export type RetryOut = components["schemas"]["RetryOut"];

export function useFilterMeta() {
  return useQuery({
    queryKey: ["meta", "filters"],
    queryFn: ({ signal }) => api<FilterMeta>("/meta/filters", { signal }),
    staleTime: Infinity,
    meta: { silent: true },
  });
}

export function useBusinesses(params: BusinessApiParams, enabled = true) {
  return useQuery({
    queryKey: ["businesses", params],
    queryFn: ({ signal }) =>
      api<BusinessPage>(`/businesses?${apiParamsToQuery(params)}`, { signal }),
    placeholderData: keepPreviousData,
    enabled,
    meta: { silent: true },
  });
}

export function useBusiness(id: string | undefined) {
  return useQuery({
    queryKey: ["business", id],
    queryFn: ({ signal }) => api<BusinessDetail>(`/businesses/${id}`, { signal }),
    enabled: !!id,
    retry: (count, error) => !(error instanceof ApiError) && count < 1,
    meta: { silent: true },
  });
}

export function useAudit(id: string | undefined) {
  return useQuery({
    queryKey: ["audit", id],
    queryFn: ({ signal }) => api<AuditEntry[]>(`/businesses/${id}/audit`, { signal }),
    enabled: !!id,
    meta: { silent: true },
  });
}

type RetryVars = { type: CheckType; key: string };

/**
 * One Idempotency-Key per click intent: created on the first click, reused by a double-click, and
 * dropped once the request settles. The error toast's Retry re-sends the same key.
 */
export function useRetryCheck(businessId: string) {
  const queryClient = useQueryClient();
  const keyRef = useRef<Partial<Record<CheckType, string | null>>>({});
  const [pending, setPending] = useState<ReadonlySet<CheckType>>(new Set());
  const resend = useRef<(vars: RetryVars) => void>(() => {});

  const mutation = useMutation({
    mutationFn: ({ type, key }: RetryVars) =>
      api<RetryOut>(`/businesses/${businessId}/checks/${type}/retry`, {
        method: "POST",
        headers: { "Idempotency-Key": key },
      }),
    meta: { silent: true },
    onMutate: ({ type }) => setPending((p) => new Set(p).add(type)),
    onSuccess: (res, { type }) => {
      const label = CHECK_LABEL[type];
      if (res.replayed) toast.info("Already processed, showing the original result.");
      else if (res.check.status === "passed") toast.success(`${label} check re-run: passed`);
      else toast.warning(`${label} check re-run: failed. ${res.check.failure_reason ?? ""}`.trim());
    },
    onError: (error, vars) => {
      const code = error instanceof ApiError ? error.code : "";
      if (code === "request_in_progress") toast.info("This retry is already running.");
      else if (code === "check_not_retryable") toast.info("This check is no longer failed.");
      else if (code === "forbidden") toast.error(error.message);
      else
        toast.error(error.message, {
          duration: 10_000,
          action: { label: "Retry", onClick: () => resend.current(vars) },
        });
    },
    onSettled: (_data, _error, { type }) => {
      keyRef.current[type] = null;
      setPending((p) => {
        const next = new Set(p);
        next.delete(type);
        return next;
      });
      // Always refresh: a 409 means our view of the check is stale.
      for (const key of [
        ["business", businessId],
        ["audit", businessId],
        ["businesses"],
        ["stats"],
      ])
        void queryClient.invalidateQueries({ queryKey: key });
    },
  });

  useEffect(() => {
    resend.current = (vars) => mutation.mutate(vars);
  });

  function retry(type: CheckType) {
    keyRef.current[type] ??= crypto.randomUUID();
    mutation.mutate({ type, key: keyRef.current[type]! });
  }

  return { retry, isPending: (type: CheckType) => pending.has(type) };
}
