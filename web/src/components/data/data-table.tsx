"use client";

import { ArrowDown, ArrowUp, ArrowUpDown } from "lucide-react";

import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { cn } from "@/lib/utils";

export type Order = "asc" | "desc";

export type Column<T> = {
  id: string;
  header: string;
  cell: (row: T) => React.ReactNode;
  /** Makes the header a sort button. */
  sortKey?: string;
  /** Direction on the first click of an unsorted column. */
  defaultOrder?: Order;
  className?: string;
  hideBelow?: "md" | "lg";
  /** Skeleton width class for loading rows. */
  skeletonClassName?: string;
};

const HIDE: Record<NonNullable<Column<unknown>["hideBelow"]>, string> = {
  md: "hidden md:table-cell",
  lg: "hidden lg:table-cell",
};

export function DataTable<T>({
  columns,
  rows,
  getRowId,
  sort,
  order,
  onSortChange,
  onRowClick,
  loading = false,
  refreshing = false,
  skeletonRows = 20,
  caption,
}: {
  columns: Column<T>[];
  rows: T[];
  getRowId: (row: T) => string;
  sort: string;
  order: Order;
  onSortChange: (sort: string, order: Order) => void;
  onRowClick?: (row: T) => void;
  loading?: boolean;
  /** Rows are kept while refetching; the table dims slightly. */
  refreshing?: boolean;
  skeletonRows?: number;
  caption: string;
}) {
  function toggleSort(col: Column<T>) {
    if (!col.sortKey) return;
    if (col.sortKey === sort) onSortChange(sort, order === "asc" ? "desc" : "asc");
    else onSortChange(col.sortKey, col.defaultOrder ?? "asc");
  }

  return (
    <div className="overflow-x-auto rounded-lg border">
      <Table
        aria-busy={loading || refreshing}
        className={cn(refreshing && "opacity-60 transition-opacity")}
      >
        <caption className="sr-only">{caption}</caption>
        <TableHeader>
          <TableRow className="hover:bg-transparent">
            {columns.map((col) => {
              const active = col.sortKey !== undefined && col.sortKey === sort;
              const Icon = !active ? ArrowUpDown : order === "asc" ? ArrowUp : ArrowDown;
              return (
                <TableHead
                  key={col.id}
                  scope="col"
                  aria-sort={
                    col.sortKey
                      ? active
                        ? order === "asc"
                          ? "ascending"
                          : "descending"
                        : "none"
                      : undefined
                  }
                  className={cn(col.hideBelow && HIDE[col.hideBelow], col.className)}
                >
                  {col.sortKey ? (
                    <button
                      type="button"
                      onClick={() => toggleSort(col)}
                      className="hover:text-foreground focus-visible:ring-ring/50 -ml-1.5 inline-flex items-center gap-1 rounded-md px-1.5 py-1 font-medium outline-none focus-visible:ring-2"
                    >
                      {col.header}
                      <Icon
                        className={cn("size-3.5", !active && "text-muted-foreground")}
                        aria-hidden="true"
                      />
                    </button>
                  ) : (
                    col.header
                  )}
                </TableHead>
              );
            })}
          </TableRow>
        </TableHeader>
        <TableBody>
          {loading
            ? Array.from({ length: skeletonRows }, (_, i) => (
                <TableRow key={i} className="hover:bg-transparent">
                  {columns.map((col) => (
                    <TableCell
                      key={col.id}
                      className={cn(col.hideBelow && HIDE[col.hideBelow], col.className)}
                    >
                      <Skeleton className={cn("h-5 w-full max-w-40", col.skeletonClassName)} />
                    </TableCell>
                  ))}
                </TableRow>
              ))
            : rows.map((row) => (
                <TableRow
                  key={getRowId(row)}
                  data-row-id={getRowId(row)}
                  onClick={onRowClick ? () => onRowClick(row) : undefined}
                  className={cn(onRowClick && "focus-within:bg-muted/60 cursor-pointer")}
                >
                  {columns.map((col) => (
                    <TableCell
                      key={col.id}
                      className={cn(col.hideBelow && HIDE[col.hideBelow], col.className)}
                    >
                      {col.cell(row)}
                    </TableCell>
                  ))}
                </TableRow>
              ))}
        </TableBody>
      </Table>
    </div>
  );
}
