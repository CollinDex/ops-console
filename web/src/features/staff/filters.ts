import { z } from "zod";

import type { components } from "@/lib/api-types";
import { appendList, getList, type SearchParamsLike } from "@/lib/url-state";
import { useUrlState } from "@/lib/use-url-state";

export type Role = components["schemas"]["Role"];

export const ROLES = ["ops_admin", "analyst", "viewer"] as const satisfies readonly Role[];
export const STAFF_SORTS = ["full_name", "role", "created_at"] as const;
export const STAFF_PAGE_SIZE = 20;

const schema = z.object({
  search: z.string().trim().max(100).catch(""),
  role: z
    .array(z.string())
    .catch([])
    .transform((v) =>
      [...new Set(v)].filter((r): r is Role => (ROLES as readonly string[]).includes(r)),
    ),
  sort: z.enum(STAFF_SORTS).catch("full_name"),
  order: z.enum(["asc", "desc"]).catch("asc"),
  page: z.coerce.number().int().min(1).max(100_000).catch(1),
});

export type StaffFilters = z.output<typeof schema>;

export function parseStaffFilters(p: SearchParamsLike): StaffFilters {
  return schema.parse({
    search: p.get("search") ?? undefined,
    role: getList(p, "role"),
    sort: p.get("sort") ?? undefined,
    order: p.get("order") ?? undefined,
    page: p.get("page") ?? undefined,
  });
}

export function serializeStaffFilters(f: StaffFilters): URLSearchParams {
  const out = new URLSearchParams();
  if (f.search) out.set("search", f.search);
  appendList(out, "role", f.role);
  if (f.sort !== "full_name") out.set("sort", f.sort);
  if (f.order !== "asc") out.set("order", f.order);
  if (f.page > 1) out.set("page", String(f.page));
  return out;
}

const KEEP: (keyof StaffFilters)[] = ["page"];

export function useStaffFilters() {
  return useUrlState<StaffFilters>({
    parse: parseStaffFilters,
    serialize: serializeStaffFilters,
    keepPage: KEEP,
  });
}
