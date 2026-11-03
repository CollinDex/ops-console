"use client";

import { Download, Loader2, SearchX } from "lucide-react";
import { useCallback, useMemo, useRef, useState } from "react";
import { toast } from "sonner";

import { EmptyState, ErrorState, isForbidden } from "@/components/data/states";
import { Pagination } from "@/components/data/pagination";
import { Forbidden } from "@/components/layout/forbidden";
import { Button } from "@/components/ui/button";
import { apiDownload } from "@/lib/api-client";
import { formatNumber } from "@/lib/format";
import { BusinessDrawer } from "./business-drawer";
import { BusinessesTable, useColumns } from "./businesses-table";
import { FilterBar } from "./filter-bar";
import { PAGE_SIZE, apiParamsToQuery, toApiParams, useBusinessFilters } from "./filters";
import { useBusinesses, useFilterMeta } from "./queries";

export function BusinessesPage() {
  const { filters, setFilters, clearAll } = useBusinessFilters();
  const meta = useFilterMeta();
  const tableTop = useRef<HTMLDivElement>(null);
  const [exporting, setExporting] = useState(false);

  const apiParams = useMemo(
    () => toApiParams(filters, meta.data?.score_bands),
    [filters, meta.data?.score_bands],
  );
  // A band in the URL needs the meta (for its range) before the first list request.
  const ready = !filters.band || meta.data !== undefined;
  const list = useBusinesses(apiParams, ready);

  const stageLabels = useMemo(
    () => Object.fromEntries((meta.data?.stages ?? []).map((s) => [s.value, s.label])),
    [meta.data?.stages],
  );
  const columns = useColumns(stageLabels);

  const onChange = useCallback(
    (patch: Parameters<typeof setFilters>[0]) => setFilters(patch),
    [setFilters],
  );

  async function exportCsv() {
    setExporting(true);
    try {
      const { blob, filename, truncated } = await apiDownload(
        `/businesses/export.csv?${apiParamsToQuery({ ...apiParams, page: undefined, page_size: undefined })}`,
      );
      const text = await blob.text();
      const count = Math.max(0, text.trim().split("\n").length - 1);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename ?? "businesses.csv";
      document.body.append(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      toast.success(
        `Exported ${formatNumber(count)} businesses${truncated ? " (export limit reached)" : ""}`,
      );
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Export failed.");
    } finally {
      setExporting(false);
    }
  }

  if (isForbidden(list.error)) return <Forbidden feature="Businesses" />;

  const data = list.data;
  const firstLoad = data === undefined && !list.isError;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-xl font-semibold">Businesses</h2>
          <p className="text-muted-foreground text-sm">
            Every SME on the marketplace, from sign-up to loan-ready
          </p>
        </div>
        <Button variant="outline" onClick={() => void exportCsv()} disabled={exporting}>
          {exporting ? (
            <Loader2 className="animate-spin" aria-hidden="true" />
          ) : (
            <Download aria-hidden="true" />
          )}
          Export CSV
        </Button>
      </div>

      <FilterBar
        filters={filters}
        meta={meta.data}
        total={data?.total}
        onChange={onChange}
        onClear={clearAll}
      />

      <div ref={tableTop} className="scroll-mt-20 space-y-3">
        {list.isError && data === undefined ? (
          <ErrorState
            error={list.error}
            retrying={list.isFetching}
            onRetry={() => void list.refetch()}
          />
        ) : data && data.items.length === 0 ? (
          <EmptyState
            icon={SearchX}
            title="No businesses match these filters"
            description="Try removing a filter or searching for something else."
            action={
              <Button variant="outline" size="sm" onClick={clearAll}>
                Clear all
              </Button>
            }
          />
        ) : (
          <BusinessesTable
            rows={data?.items ?? []}
            columns={columns}
            sort={filters.sort}
            order={filters.order}
            onSortChange={(sort, order) => setFilters({ sort: sort as typeof filters.sort, order })}
            onOpen={(b) => setFilters({ id: b.id })}
            loading={firstLoad || !ready}
            refreshing={list.isFetching && data !== undefined}
          />
        )}
        {data && data.total > 0 && (
          <Pagination
            page={data.page}
            pageSize={PAGE_SIZE}
            total={data.total}
            onPageChange={(page) => {
              setFilters({ page });
              tableTop.current?.scrollIntoView({ behavior: "smooth", block: "start" });
            }}
          />
        )}
      </div>

      <BusinessDrawer id={filters.id} onClose={() => setFilters({ id: undefined })} />
    </div>
  );
}
