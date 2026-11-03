"use client";

import { BadgeCheck, Building2, Gauge, OctagonAlert, type LucideIcon } from "lucide-react";
import Link from "next/link";

import { ErrorState } from "@/components/data/states";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useAuth } from "@/features/auth/auth-provider";
import { formatNumber } from "@/lib/format";
import { bandFor } from "@/lib/score";
import { useOverviewStats, type OverviewStats } from "./queries";

type CardDef = {
  key: string;
  label: string;
  icon: LucideIcon;
  value: (c: OverviewStats["cards"]) => string;
  sub: (c: OverviewStats["cards"]) => string;
  definition: string;
  href?: string;
  tone?: string;
};

const CARDS: CardDef[] = [
  {
    key: "total",
    label: "Total businesses",
    icon: Building2,
    value: (c) => formatNumber(c.total_businesses),
    sub: () => "On the marketplace",
    definition: "Every SME that has signed up.",
  },
  {
    key: "verified",
    label: "Fully verified",
    icon: BadgeCheck,
    value: (c) => formatNumber(c.fully_verified),
    sub: (c) =>
      c.total_businesses
        ? `${Math.round((c.fully_verified / c.total_businesses) * 100)}% of total`
        : "—",
    definition: "All four checks passed.",
    tone: "text-success",
  },
  {
    key: "stuck",
    label: "Stuck in onboarding",
    icon: OctagonAlert,
    value: (c) => formatNumber(c.stuck),
    sub: () => "Failed check, or more than 7 days in onboarding",
    definition: "Not profile ready, and a check failed or sign-up is over 7 days old.",
    href: "/businesses?failed=any",
    tone: "text-danger",
  },
  {
    key: "score",
    label: "Average credit score",
    icon: Gauge,
    value: (c) => (c.avg_credit_score === null ? "—" : String(Math.round(c.avg_credit_score))),
    sub: (c) => (c.avg_credit_score === null ? "No scores yet" : bandFor(c.avg_credit_score).label),
    definition: "Mean of scored businesses.",
  },
];

export function StatCards() {
  const query = useOverviewStats();
  const { hasRole } = useAuth();
  const canDrill = hasRole("analyst", "ops_admin");

  if (query.data === undefined && query.isError) {
    return (
      <Card className="sm:col-span-2 lg:col-span-4">
        <CardContent>
          <ErrorState
            compact
            error={query.error}
            retrying={query.isFetching}
            onRetry={() => void query.refetch()}
          />
        </CardContent>
      </Card>
    );
  }

  return (
    <>
      {CARDS.map((def) => {
        const cards = query.data?.cards;
        const Icon = def.icon;
        const body = (
          <Card className="group-hover/stat:bg-muted/40 h-full gap-2 transition-colors">
            <CardContent className="space-y-1">
              <div className="text-muted-foreground flex items-center justify-between text-sm">
                <span>{def.label}</span>
                <Icon className={`size-4 ${def.tone ?? ""}`} aria-hidden="true" />
              </div>
              {cards ? (
                <>
                  <p className="font-mono text-3xl font-semibold tabular-nums">
                    {def.value(cards)}
                  </p>
                  <p className="text-sm">{def.sub(cards)}</p>
                </>
              ) : (
                <>
                  <Skeleton className="h-9 w-20" />
                  <Skeleton className="h-4 w-32" />
                </>
              )}
              <p className="text-muted-foreground text-xs">{def.definition}</p>
            </CardContent>
          </Card>
        );
        return def.href && canDrill ? (
          <Link
            key={def.key}
            href={def.href}
            className="group/stat focus-visible:ring-ring/50 block rounded-xl outline-none focus-visible:ring-3"
            aria-label={`${def.label}: view in Businesses`}
          >
            {body}
          </Link>
        ) : (
          <div key={def.key}>{body}</div>
        );
      })}
    </>
  );
}
