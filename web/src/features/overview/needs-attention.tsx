"use client";

import { CircleX, Clock } from "lucide-react";
import Link from "next/link";

import { EmptyState } from "@/components/data/states";
import { StageBadge } from "@/components/data/stage-badge";
import { Skeleton } from "@/components/ui/skeleton";
import { useAuth } from "@/features/auth/auth-provider";
import { formatRelative } from "@/lib/format";
import { cn } from "@/lib/utils";
import { Block } from "./block";
import { useOverviewStats, type OverviewStats } from "./queries";

type Item = OverviewStats["needs_attention"][number];

function Reasons({ reasons }: { reasons: Item["reasons"] }) {
  return (
    <ul className="flex flex-wrap gap-1.5">
      {reasons.map((r, i) => {
        const failed = r.kind === "failed_check";
        const Icon = failed ? CircleX : Clock;
        return (
          <li
            key={i}
            className={cn(
              "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium",
              failed ? "bg-danger/10 text-danger" : "bg-warning/10 text-warning",
            )}
          >
            <Icon className="size-3" aria-hidden="true" />
            {r.label}
          </li>
        );
      })}
    </ul>
  );
}

function Row({ item, link }: { item: Item; link: boolean }) {
  const content = (
    <>
      <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
        <span className="font-medium">{item.name}</span>
        <StageBadge stage={item.stage} />
        <span className="text-muted-foreground ml-auto text-xs whitespace-nowrap">
          {formatRelative(item.since)}
        </span>
      </div>
      <Reasons reasons={item.reasons} />
    </>
  );
  return link ? (
    <Link
      href={`/businesses?id=${item.id}`}
      className="hover:bg-muted/50 focus-visible:ring-ring/50 block space-y-1.5 rounded-md px-2 py-2.5 outline-none focus-visible:ring-2"
    >
      {content}
    </Link>
  ) : (
    <div className="space-y-1.5 px-2 py-2.5">{content}</div>
  );
}

export function NeedsAttention() {
  const query = useOverviewStats();
  const { hasRole } = useAuth();
  const canOpen = hasRole("analyst", "ops_admin");

  return (
    <Block
      title="Needs attention"
      description="A check failed, or bank data is more than 7 days old."
      query={query}
      className="lg:col-span-2"
      skeleton={
        <div className="space-y-3">
          {Array.from({ length: 5 }, (_, i) => (
            <Skeleton key={i} className="h-12 w-full" />
          ))}
        </div>
      }
    >
      {(data) =>
        data.needs_attention.length === 0 ? (
          <EmptyState compact title="Nothing needs attention right now." />
        ) : (
          <ul className="divide-y">
            {data.needs_attention.slice(0, 10).map((item) => (
              <li key={item.id}>
                <Row item={item} link={canOpen} />
              </li>
            ))}
          </ul>
        )
      }
    </Block>
  );
}
