"use client";

import { ChevronLeft, ChevronRight } from "lucide-react";

import { Button } from "@/components/ui/button";
import { formatNumber } from "@/lib/format";
import { cn } from "@/lib/utils";

/** Up to 7 slots: 1 … 4 5 6 … 20. */
export function pageItems(
  page: number,
  pages: number,
): (number | "ellipsis-start" | "ellipsis-end")[] {
  if (pages <= 7) return Array.from({ length: pages }, (_, i) => i + 1);
  if (page <= 4) return [1, 2, 3, 4, 5, "ellipsis-end", pages];
  if (page >= pages - 3)
    return [1, "ellipsis-start", pages - 4, pages - 3, pages - 2, pages - 1, pages];
  return [1, "ellipsis-start", page - 1, page, page + 1, "ellipsis-end", pages];
}

export function Pagination({
  page,
  pageSize,
  total,
  onPageChange,
  className,
}: {
  page: number;
  pageSize: number;
  total: number;
  onPageChange: (page: number) => void;
  className?: string;
}) {
  const pages = Math.max(1, Math.ceil(total / pageSize));
  const from = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const to = Math.min(page * pageSize, total);
  return (
    <nav
      aria-label="Pagination"
      className={cn("flex flex-wrap items-center justify-between gap-3", className)}
    >
      <p className="text-muted-foreground text-sm tabular-nums" aria-live="polite">
        Showing {formatNumber(from)}–{formatNumber(to)} of {formatNumber(total)}
      </p>
      <div className="flex items-center gap-1">
        <Button
          variant="outline"
          size="sm"
          disabled={page <= 1}
          onClick={() => onPageChange(page - 1)}
        >
          <ChevronLeft aria-hidden="true" />
          Previous
        </Button>
        <ul className="hidden items-center gap-1 sm:flex">
          {pageItems(page, pages).map((item) =>
            typeof item === "string" ? (
              <li key={item} aria-hidden="true" className="text-muted-foreground px-1">
                …
              </li>
            ) : (
              <li key={item}>
                <Button
                  variant={item === page ? "default" : "ghost"}
                  size="sm"
                  className="min-w-7 tabular-nums"
                  aria-current={item === page ? "page" : undefined}
                  aria-label={`Page ${item}`}
                  onClick={() => item !== page && onPageChange(item)}
                >
                  {item}
                </Button>
              </li>
            ),
          )}
        </ul>
        <Button
          variant="outline"
          size="sm"
          disabled={page >= pages}
          onClick={() => onPageChange(page + 1)}
        >
          Next
          <ChevronRight aria-hidden="true" />
        </Button>
      </div>
    </nav>
  );
}
