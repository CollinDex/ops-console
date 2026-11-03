import { useUrlState } from "@/lib/use-url-state";
import { appendList, getList, type SearchParamsLike } from "@/lib/url-state";
import type { components, operations } from "@/lib/api-types";
import { z } from "zod";

export type Stage = components["schemas"]["Stage"];
export type Sector = components["schemas"]["Sector"];
export type CheckType = components["schemas"]["CheckType"];
export type ScoreBand = components["schemas"]["ScoreBandOut"];

export const PAGE_SIZE = 20;

export const STAGES = [
  "signed_up",
  "documents_submitted",
  "checks_in_progress",
  "bank_linked",
  "profile_ready",
] as const satisfies readonly Stage[];

export const SECTORS = [
  "agriculture",
  "retail",
  "manufacturing",
  "logistics",
  "technology",
  "healthcare",
  "hospitality",
  "construction",
  "fashion",
  "education",
] as const satisfies readonly Sector[];

export const FAILED_VALUES = ["any", "cac", "tin", "bvn", "bank_link"] as const;
export const SORT_KEYS = ["name", "credit_score", "created_at", "last_bank_sync_at"] as const;

export const DEFAULT_SORT = "created_at";
export const DEFAULT_ORDER = "desc";

const BAND_KEY = /^[a-z_]{1,20}$/;

/** A list param keeps only the allowed values, de-duplicated, in first-seen order. */
function oneOfList<T extends string>(allowed: readonly T[]) {
  return z
    .array(z.string())
    .catch([])
    .transform((vals) =>
      [...new Set(vals)].filter((v): v is T => (allowed as readonly string[]).includes(v)),
    );
}

export const businessFiltersSchema = z.object({
  search: z.string().trim().max(100).catch(""),
  stage: oneOfList(STAGES),
  sector: oneOfList(SECTORS),
  band: z.string().regex(BAND_KEY).optional().catch(undefined),
  failed: z.enum(FAILED_VALUES).optional().catch(undefined),
  sort: z.enum(SORT_KEYS).catch(DEFAULT_SORT),
  order: z.enum(["asc", "desc"]).catch(DEFAULT_ORDER),
  page: z.coerce.number().int().min(1).max(100_000).catch(1),
  id: z.uuid().optional().catch(undefined),
});

export type Filters = z.output<typeof businessFiltersSchema>;

export function parseFilters(params: SearchParamsLike): Filters {
  return businessFiltersSchema.parse({
    search: params.get("search") ?? undefined,
    stage: getList(params, "stage"),
    sector: getList(params, "sector"),
    band: params.get("band") ?? undefined,
    failed: params.get("failed") ?? undefined,
    sort: params.get("sort") ?? undefined,
    order: params.get("order") ?? undefined,
    page: params.get("page") ?? undefined,
    id: params.get("id") ?? undefined,
  });
}

/** Defaults are dropped, so a clean view has a clean URL. */
export function serializeFilters(f: Filters): URLSearchParams {
  const out = new URLSearchParams();
  if (f.search) out.set("search", f.search);
  appendList(out, "stage", f.stage);
  appendList(out, "sector", f.sector);
  if (f.band) out.set("band", f.band);
  if (f.failed) out.set("failed", f.failed);
  if (f.sort !== DEFAULT_SORT) out.set("sort", f.sort);
  if (f.order !== DEFAULT_ORDER) out.set("order", f.order);
  if (f.page > 1) out.set("page", String(f.page));
  if (f.id) out.set("id", f.id);
  return out;
}

export type BusinessApiParams = NonNullable<
  operations["list_businesses_api_v1_businesses_get"]["parameters"]["query"]
>;

/** Map UI state onto the API query. `id` (the open drawer) is not part of the list query. */
export function toApiParams(f: Filters, bands: readonly ScoreBand[] = []): BusinessApiParams {
  const params: BusinessApiParams = {
    sort: f.sort,
    order: f.order,
    page: f.page,
    page_size: PAGE_SIZE,
  };
  if (f.search) params.search = f.search;
  if (f.stage.length) params.stage = f.stage;
  if (f.sector.length) params.sector = f.sector;
  const band = bands.find((b) => b.key === f.band);
  if (band) {
    params.score_min = band.min;
    params.score_max = band.max;
  }
  if (f.failed) params.failed_check = f.failed;
  return params;
}

export function apiParamsToQuery(params: BusinessApiParams): string {
  const out = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null) continue;
    if (Array.isArray(value)) appendList(out, key, value);
    else out.set(key, String(value));
  }
  return out.toString();
}

/** Number of active filters (not counting sort, page or the open drawer). */
export function activeFilterCount(f: Filters): number {
  return (
    (f.search ? 1 : 0) + f.stage.length + f.sector.length + (f.band ? 1 : 0) + (f.failed ? 1 : 0)
  );
}

const KEEP_PAGE: (keyof Filters)[] = ["page", "id"];

export function useBusinessFilters() {
  return useUrlState<Filters>({
    parse: parseFilters,
    serialize: serializeFilters,
    keepPage: KEEP_PAGE,
  });
}
