"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useMemo, useRef } from "react";

import { mergeFilters } from "@/lib/url-state";

type Options<F extends { page: number }> = {
  parse: (params: URLSearchParams) => F;
  serialize: (filters: F) => URLSearchParams;
  /** Keys whose change must not reset `page` to 1. */
  keepPage: (keyof F)[];
};

/**
 * The URL is the single source of truth for table state (ADR-007). Filters are derived from the
 * search params on every render; updates go through router.replace without scrolling.
 */
export function useUrlState<F extends { page: number }>({
  parse,
  serialize,
  keepPage,
}: Options<F>) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const qs = searchParams.toString();

  const filters = useMemo(() => parse(new URLSearchParams(qs)), [parse, qs]);

  // Lets two setFilters calls in the same tick compose before the URL has caught up.
  const latest = useRef(filters);
  latest.current = filters;

  const write = useCallback(
    (next: F) => {
      latest.current = next;
      const out = serialize(next).toString();
      router.replace(out ? `${pathname}?${out}` : pathname, { scroll: false });
    },
    [router, pathname, serialize],
  );

  const setFilters = useCallback(
    (patch: Partial<F>, opts: { resetPage?: boolean } = {}) => {
      write(mergeFilters(latest.current, patch, { resetPage: opts.resetPage, keepPage }));
    },
    [write, keepPage],
  );

  const clearAll = useCallback(() => write(parse(new URLSearchParams())), [write, parse]);

  return { filters, setFilters, clearAll };
}
