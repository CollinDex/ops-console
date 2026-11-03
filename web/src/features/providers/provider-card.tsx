"use client";

import { ChevronDown } from "lucide-react";
import { useState } from "react";

import { ProviderStatusBadge } from "@/components/data/status-badges";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatRelative } from "@/lib/format";
import { cn } from "@/lib/utils";
import { IncidentList } from "./incidents";
import { USED_BY, useSimulateProvider, type ProviderMode, type ProviderStatus } from "./queries";
import { Sparkline } from "./sparkline";

const MODES: { value: ProviderMode; label: string }[] = [
  { value: "up", label: "Up" },
  { value: "slow", label: "Slow" },
  { value: "down", label: "Down" },
];

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-muted-foreground text-xs">{label}</dt>
      <dd className="font-mono text-sm tabular-nums">{value}</dd>
    </div>
  );
}

function SimulateControl({ provider }: { provider: ProviderStatus }) {
  const simulate = useSimulateProvider(provider.name, provider.label);
  const labelId = `simulate-${provider.name}`;
  return (
    <div className="space-y-1.5">
      <p id={labelId} className="text-muted-foreground text-xs font-medium">
        Simulate (demo only)
      </p>
      <div
        role="radiogroup"
        aria-labelledby={labelId}
        className="bg-muted inline-flex rounded-lg p-0.5"
      >
        {MODES.map((m) => {
          const selected = provider.mode === m.value;
          return (
            <button
              key={m.value}
              type="button"
              role="radio"
              aria-checked={selected}
              disabled={simulate.isPending}
              onClick={() => {
                if (!selected) simulate.mutate(m.value);
              }}
              className={cn(
                "focus-visible:ring-ring/60 min-h-10 rounded-md px-4 text-sm font-medium outline-none focus-visible:ring-2 disabled:opacity-60 sm:min-h-8 sm:px-3",
                selected
                  ? "bg-card text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground",
              )}
            >
              {m.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}

export function ProviderCard({
  provider,
  isAdmin,
}: {
  provider: ProviderStatus;
  isAdmin: boolean;
}) {
  const [open, setOpen] = useState(false);
  const p = provider;
  const panelId = `incidents-${p.name}`;
  return (
    <Card className="gap-4">
      <CardHeader className="flex-row items-center justify-between gap-2">
        <CardTitle>{p.label}</CardTitle>
        <ProviderStatusBadge status={p.status} />
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="font-mono text-2xl font-medium tabular-nums">
              {p.latency_ms === null ? "—" : `${p.latency_ms} ms`}
            </p>
            <p className="text-muted-foreground text-xs">
              {p.last_checked_at
                ? `Checked ${formatRelative(p.last_checked_at)}`
                : "Not checked yet"}
            </p>
          </div>
          <Sparkline points={p.recent} current={p.latency_ms} />
        </div>
        <dl className="grid grid-cols-2 gap-3">
          <Stat
            label="24 h uptime"
            value={p.uptime_24h === null ? "—" : `${p.uptime_24h.toFixed(1)}%`}
          />
          <Stat
            label="24 h avg latency"
            value={p.avg_latency_24h === null ? "—" : `${p.avg_latency_24h} ms`}
          />
        </dl>
        <p className="text-muted-foreground text-sm">Used by: {USED_BY[p.name]}</p>
        {isAdmin && <SimulateControl provider={p} />}
        <div className="border-t pt-3">
          <Button
            variant="ghost"
            size="sm"
            aria-expanded={open}
            aria-controls={panelId}
            onClick={() => setOpen((v) => !v)}
            className="-ml-2.5 min-h-10 sm:min-h-7"
          >
            <ChevronDown
              className={cn("transition-transform", open && "rotate-180")}
              aria-hidden="true"
            />
            {open ? "Hide incidents" : "View incidents"}
          </Button>
          {open && (
            <div id={panelId} className="mt-2">
              <IncidentList name={p.name} />
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
