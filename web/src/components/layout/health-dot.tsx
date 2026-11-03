"use client";

import { useQuery } from "@tanstack/react-query";
import { CircleCheck, CircleX, Loader, TriangleAlert, type LucideIcon } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { api } from "@/lib/api-client";
import type { components } from "@/lib/api-types";
import { formatDateTime } from "@/lib/format";
import { cn } from "@/lib/utils";

export type HealthResponse = components["schemas"]["HealthOut"];

type DotState = "checking" | "ok" | "degraded" | "down";

const STYLE: Record<DotState, { icon: LucideIcon; className: string }> = {
  checking: { icon: Loader, className: "text-muted-foreground animate-pulse" },
  ok: { icon: CircleCheck, className: "text-success" },
  degraded: { icon: TriangleAlert, className: "text-warning" },
  down: { icon: CircleX, className: "text-danger" },
};

function secondsAgo(ts: number, now: number): string {
  const s = Math.max(0, Math.round((now - ts) / 1000));
  return s < 60 ? `${s} s ago` : `${Math.round(s / 60)} min ago`;
}

export function HealthDot() {
  const { data, isError, isPending, dataUpdatedAt, errorUpdatedAt } = useQuery({
    queryKey: ["health"],
    queryFn: ({ signal }) => api<HealthResponse>("/health", { signal }),
    refetchInterval: 30_000,
    retry: false,
    meta: { silent: true, background: true },
  });

  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 5_000);
    return () => clearInterval(id);
  }, []);

  let state: DotState;
  let label: string;
  if (isPending) {
    state = "checking";
    label = "Checking…";
  } else if (isError || data?.status === "down" || data?.db === "down") {
    state = "down";
    label = "API unreachable";
  } else if (data?.status === "degraded") {
    state = "degraded";
    const n = (data.providers?.slow ?? 0) + (data.providers?.down ?? 0);
    label = `${n} provider${n === 1 ? "" : "s"} degraded`;
  } else {
    state = "ok";
    label = "All systems normal";
  }

  const { icon: Icon, className } = STYLE[state];
  const checkedAt = Math.max(dataUpdatedAt, errorUpdatedAt);

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Link
          href="/providers"
          role="status"
          className="hover:bg-muted focus-visible:ring-ring/60 flex h-8 items-center gap-1.5 rounded-lg px-2 text-sm font-medium outline-none focus-visible:ring-2"
        >
          <Icon className={cn("size-4 shrink-0", className)} aria-hidden="true" />
          <span className={cn("sr-only sm:not-sr-only", className)}>{label}</span>
        </Link>
      </TooltipTrigger>
      <TooltipContent>
        <div>{checkedAt ? `Last checked ${secondsAgo(checkedAt, now)}` : "Checking…"}</div>
        {data?.time && <div className="opacity-70">Server time {formatDateTime(data.time)}</div>}
      </TooltipContent>
    </Tooltip>
  );
}
