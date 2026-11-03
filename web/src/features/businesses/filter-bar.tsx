"use client";

import { X } from "lucide-react";
import { useCallback, useMemo } from "react";

import { MultiSelect } from "@/components/data/multi-select";
import { SearchInput } from "@/components/data/search-input";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { formatNumber } from "@/lib/format";
import { activeFilterCount, type Filters } from "./filters";
import type { FilterMeta } from "./queries";

const ANY = "__any__";

const FAILED_OPTIONS = [
  { value: ANY, label: "Any status" },
  { value: "any", label: "Has a failed check" },
  { value: "cac", label: "CAC failed" },
  { value: "tin", label: "Tax ID failed" },
  { value: "bvn", label: "BVN failed" },
  { value: "bank_link", label: "Bank link failed" },
];

function Chip({ label, onRemove }: { label: string; onRemove: () => void }) {
  return (
    <li>
      <button
        type="button"
        onClick={onRemove}
        aria-label={`Remove filter: ${label}`}
        className="bg-secondary text-secondary-foreground hover:bg-muted focus-visible:ring-ring/50 inline-flex items-center gap-1 rounded-full py-0.5 pr-1.5 pl-2.5 text-xs font-medium outline-none focus-visible:ring-2"
      >
        {label}
        <X className="size-3" aria-hidden="true" />
      </button>
    </li>
  );
}

export function FilterBar({
  filters,
  meta,
  total,
  onChange,
  onClear,
}: {
  filters: Filters;
  meta: FilterMeta | undefined;
  total: number | undefined;
  onChange: (patch: Partial<Filters>) => void;
  onClear: () => void;
}) {
  const commitSearch = useCallback((search: string) => onChange({ search }), [onChange]);
  const active = activeFilterCount(filters);

  const stageLabel = (v: string) => meta?.stages.find((o) => o.value === v)?.label ?? v;
  const sectorLabel = (v: string) => meta?.sectors.find((o) => o.value === v)?.label ?? v;
  const band = meta?.score_bands.find((b) => b.key === filters.band);
  const failedLabel = FAILED_OPTIONS.find((o) => o.value === filters.failed)?.label;

  const chips = useMemo(() => {
    const list: { key: string; label: string; remove: () => void }[] = [];
    if (filters.search)
      list.push({
        key: "search",
        label: `Search: ${filters.search}`,
        remove: () => onChange({ search: "" }),
      });
    for (const s of filters.stage)
      list.push({
        key: `stage-${s}`,
        label: `Stage: ${stageLabel(s)}`,
        remove: () => onChange({ stage: filters.stage.filter((v) => v !== s) }),
      });
    for (const s of filters.sector)
      list.push({
        key: `sector-${s}`,
        label: `Sector: ${sectorLabel(s)}`,
        remove: () => onChange({ sector: filters.sector.filter((v) => v !== s) }),
      });
    if (filters.band)
      list.push({
        key: "band",
        label: `Score: ${band?.label ?? filters.band}`,
        remove: () => onChange({ band: undefined }),
      });
    if (filters.failed)
      list.push({
        key: "failed",
        label: failedLabel ?? filters.failed,
        remove: () => onChange({ failed: undefined }),
      });
    return list;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters, meta, onChange]);

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <SearchInput
          value={filters.search}
          onCommit={commitSearch}
          placeholder="Search name, CAC number or director"
          label="Search businesses"
          className="sm:max-w-sm"
        />
        <MultiSelect
          label="Stage"
          options={meta?.stages ?? []}
          selected={filters.stage}
          onChange={(stage) => onChange({ stage: stage as Filters["stage"] })}
        />
        <MultiSelect
          label="Sector"
          searchable
          options={meta?.sectors ?? []}
          selected={filters.sector}
          onChange={(sector) => onChange({ sector: sector as Filters["sector"] })}
        />
        <Select
          value={filters.band ?? ANY}
          onValueChange={(v) => onChange({ band: v === ANY ? undefined : v })}
        >
          <SelectTrigger aria-label="Score band filter">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ANY}>Any score</SelectItem>
            {meta?.score_bands.map((b) => (
              <SelectItem key={b.key} value={b.key}>
                {b.label} ({b.min}–{b.max})
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select
          value={filters.failed ?? ANY}
          onValueChange={(v) =>
            onChange({ failed: v === ANY ? undefined : (v as Filters["failed"]) })
          }
        >
          <SelectTrigger aria-label="Failed check filter">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {FAILED_OPTIONS.map((o) => (
              <SelectItem key={o.value} value={o.value}>
                {o.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      <div className="flex min-h-7 flex-wrap items-center gap-x-3 gap-y-2">
        <p className="text-sm tabular-nums" aria-live="polite">
          {total === undefined
            ? "Loading…"
            : `${formatNumber(total)} business${total === 1 ? "" : "es"}`}
        </p>
        {active > 0 && (
          <>
            <ul className="flex flex-wrap items-center gap-1.5" aria-label="Active filters">
              {chips.map((c) => (
                <Chip key={c.key} label={c.label} onRemove={c.remove} />
              ))}
            </ul>
            <Button variant="ghost" size="sm" onClick={onClear}>
              Clear all
            </Button>
          </>
        )}
      </div>
    </div>
  );
}
