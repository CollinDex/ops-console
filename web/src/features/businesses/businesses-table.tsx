"use client";

import { TriangleAlert } from "lucide-react";

import { DataTable, type Column, type Order } from "@/components/data/data-table";
import { ScorePill } from "@/components/data/score-pill";
import { StageBadge } from "@/components/data/stage-badge";
import { CHECK_ORDER, CheckBadge } from "@/components/data/status-badges";
import { formatDate, formatRelative } from "@/lib/format";
import type { BusinessListItem } from "./queries";

export function useColumns(stageLabels: Record<string, string>): Column<BusinessListItem>[] {
  return [
    {
      id: "name",
      header: "Business",
      sortKey: "name",
      className: "min-w-52 whitespace-normal",
      skeletonClassName: "max-w-48",
      cell: (b) => (
        <div className="space-y-0.5">
          <button
            type="button"
            data-row-focus={b.id}
            className="focus-visible:ring-ring/50 rounded-sm text-left font-medium outline-none hover:underline focus-visible:ring-2"
          >
            {b.name}
          </button>
          <p className="text-muted-foreground text-xs">
            {b.state} · <span className="font-mono">{b.cac_number}</span>
          </p>
        </div>
      ),
    },
    {
      id: "sector",
      header: "Sector",
      hideBelow: "md",
      cell: (b) => <span className="capitalize">{b.sector}</span>,
    },
    {
      id: "stage",
      header: "Stage",
      cell: (b) => <StageBadge stage={b.stage} label={stageLabels[b.stage]} />,
    },
    {
      id: "checks",
      header: "Checks",
      cell: (b) => (
        <div className="flex gap-1">
          {CHECK_ORDER.map((t) => (
            <CheckBadge key={t} type={t} status={b.checks[t] ?? "pending"} />
          ))}
        </div>
      ),
    },
    {
      id: "score",
      header: "Score",
      sortKey: "credit_score",
      defaultOrder: "desc",
      cell: (b) => <ScorePill score={b.credit_score} />,
    },
    {
      id: "sync",
      header: "Last bank sync",
      sortKey: "last_bank_sync_at",
      defaultOrder: "desc",
      hideBelow: "md",
      cell: (b) =>
        b.last_bank_sync_at ? (
          <span className="flex items-center gap-2">
            <span title={formatDate(b.last_bank_sync_at)}>
              {formatRelative(b.last_bank_sync_at)}
            </span>
            {b.bank_data_stale && (
              <span className="bg-warning/10 text-warning inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium">
                <TriangleAlert className="size-3" aria-hidden="true" />
                Stale
              </span>
            )}
          </span>
        ) : (
          <span className="text-muted-foreground">—</span>
        ),
    },
    {
      id: "joined",
      header: "Joined",
      sortKey: "created_at",
      defaultOrder: "desc",
      hideBelow: "lg",
      cell: (b) => formatDate(b.created_at),
    },
  ];
}

export function BusinessesTable({
  rows,
  columns,
  sort,
  order,
  onSortChange,
  onOpen,
  loading,
  refreshing,
}: {
  rows: BusinessListItem[];
  columns: Column<BusinessListItem>[];
  sort: string;
  order: Order;
  onSortChange: (sort: string, order: Order) => void;
  onOpen: (b: BusinessListItem) => void;
  loading: boolean;
  refreshing: boolean;
}) {
  return (
    <DataTable
      caption="Businesses"
      columns={columns}
      rows={rows}
      getRowId={(b) => b.id}
      sort={sort}
      order={order}
      onSortChange={onSortChange}
      onRowClick={onOpen}
      loading={loading}
      refreshing={refreshing}
    />
  );
}
