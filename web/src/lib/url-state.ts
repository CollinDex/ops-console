/** Pure helpers behind the URL-as-state hooks (ADR-007). Kept free of Next imports for testing. */

export type SearchParamsLike = Pick<URLSearchParams, "get" | "getAll">;

/**
 * Apply a patch to the current filters. Any change other than the keys in `keepPage` resets
 * `page` to 1, unless the caller opts out with `resetPage: false`.
 */
export function mergeFilters<F extends { page: number }>(
  current: F,
  patch: Partial<F>,
  opts: { resetPage?: boolean; keepPage: (keyof F)[] },
): F {
  const next = { ...current, ...patch };
  const changesFilter = (Object.keys(patch) as (keyof F)[]).some(
    (k) => !opts.keepPage.includes(k) && !sameValue(current[k], patch[k]),
  );
  if ((opts.resetPage ?? true) && changesFilter && !("page" in patch)) next.page = 1;
  return next;
}

function sameValue(a: unknown, b: unknown): boolean {
  return JSON.stringify(a) === JSON.stringify(b);
}

/** Read a repeated key such as `stage=a&stage=b`, treating empty values as absent. */
export function getList(params: SearchParamsLike, key: string): string[] {
  return params.getAll(key).filter((v) => v !== "");
}

export function appendList(out: URLSearchParams, key: string, values: readonly string[]): void {
  for (const v of values) out.append(key, v);
}
