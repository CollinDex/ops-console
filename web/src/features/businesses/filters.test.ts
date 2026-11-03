import { describe, expect, it } from "vitest";

import { mergeFilters } from "@/lib/url-state";
import {
  activeFilterCount,
  apiParamsToQuery,
  parseFilters,
  serializeFilters,
  toApiParams,
  type Filters,
  type ScoreBand,
} from "./filters";

const BANDS: ScoreBand[] = [
  { key: "poor", label: "Poor", min: 300, max: 579 },
  { key: "good", label: "Good", min: 670, max: 739 },
];

const parse = (qs: string) => parseFilters(new URLSearchParams(qs));

describe("parseFilters", () => {
  it("returns defaults for an empty query", () => {
    expect(parse("")).toEqual({
      search: "",
      stage: [],
      sector: [],
      band: undefined,
      failed: undefined,
      sort: "created_at",
      order: "desc",
      page: 1,
      id: undefined,
    });
  });

  it("reads repeated keys as arrays", () => {
    const f = parse("stage=signed_up&stage=bank_linked&sector=retail&sector=fashion");
    expect(f.stage).toEqual(["signed_up", "bank_linked"]);
    expect(f.sector).toEqual(["retail", "fashion"]);
  });

  it("falls back silently on invalid values", () => {
    const f = parse(
      "stage=nope&stage=bank_linked&sector=x&failed=zzz&sort=password&order=sideways&page=-4&band=BAD!&id=not-a-uuid",
    );
    expect(f.stage).toEqual(["bank_linked"]);
    expect(f.sector).toEqual([]);
    expect(f.failed).toBeUndefined();
    expect(f.sort).toBe("created_at");
    expect(f.order).toBe("desc");
    expect(f.page).toBe(1);
    expect(f.band).toBeUndefined();
    expect(f.id).toBeUndefined();
  });

  it("falls back on a non-numeric page and over-long search", () => {
    expect(parse("page=abc").page).toBe(1);
    expect(parse("page=0").page).toBe(1);
    expect(parse(`search=${"a".repeat(200)}`).search).toBe("");
  });
});

describe("serializeFilters", () => {
  it("omits defaults", () => {
    expect(serializeFilters(parse("")).toString()).toBe("");
    expect(serializeFilters(parse("sort=created_at&order=desc&page=1")).toString()).toBe("");
  });

  it("round-trips a full filter set", () => {
    const id = "4f6c1d2e-8a3b-4c5d-9e6f-7a8b9c0d1e2f";
    const qs = `search=ade&stage=checks_in_progress&stage=bank_linked&sector=retail&band=good&failed=bvn&sort=credit_score&order=asc&page=3&id=${id}`;
    const filters = parse(qs);
    const again = parse(serializeFilters(filters).toString());
    expect(again).toEqual(filters);
    expect(serializeFilters(filters).toString()).toBe(qs);
  });

  it("writes arrays as repeated keys", () => {
    const f = parse("stage=signed_up&stage=profile_ready");
    expect(serializeFilters(f).getAll("stage")).toEqual(["signed_up", "profile_ready"]);
  });
});

describe("toApiParams", () => {
  it("maps the band to score_min and score_max", () => {
    const p = toApiParams(parse("band=good"), BANDS);
    expect(p.score_min).toBe(670);
    expect(p.score_max).toBe(739);
  });

  it("ignores an unknown band and maps failed to failed_check", () => {
    const p = toApiParams(parse("band=nope&failed=any"), BANDS);
    expect(p.score_min).toBeUndefined();
    expect(p.failed_check).toBe("any");
  });

  it("never sends the open drawer id and always sends paging", () => {
    const p = toApiParams(parse("id=4f6c1d2e-8a3b-4c5d-9e6f-7a8b9c0d1e2f&page=2"), BANDS);
    expect(p).toEqual({ sort: "created_at", order: "desc", page: 2, page_size: 20 });
  });

  it("builds a query string with repeated keys", () => {
    const q = apiParamsToQuery(toApiParams(parse("stage=signed_up&stage=bank_linked&search=ade")));
    const sp = new URLSearchParams(q);
    expect(sp.getAll("stage")).toEqual(["signed_up", "bank_linked"]);
    expect(sp.get("search")).toBe("ade");
    expect(sp.get("page_size")).toBe("20");
  });
});

describe("mergeFilters (page reset)", () => {
  const keepPage: (keyof Filters)[] = ["page", "id"];
  const base = parse("page=4&search=ade");

  it("resets page to 1 when a filter changes", () => {
    expect(mergeFilters(base, { failed: "bvn" }, { keepPage }).page).toBe(1);
    expect(mergeFilters(base, { sort: "name" }, { keepPage }).page).toBe(1);
  });

  it("keeps the page when only page or id change", () => {
    expect(mergeFilters(base, { page: 5 }, { keepPage }).page).toBe(5);
    expect(mergeFilters(base, { id: "x" }, { keepPage }).page).toBe(4);
  });

  it("keeps the page when resetPage is false or the value is unchanged", () => {
    expect(mergeFilters(base, { failed: "bvn" }, { keepPage, resetPage: false }).page).toBe(4);
    expect(mergeFilters(base, { search: "ade" }, { keepPage }).page).toBe(4);
  });
});

describe("activeFilterCount", () => {
  it("counts search, list items, band and failed", () => {
    expect(activeFilterCount(parse(""))).toBe(0);
    expect(
      activeFilterCount(parse("search=a&stage=signed_up&stage=bank_linked&band=good&failed=bvn")),
    ).toBe(5);
  });
});
