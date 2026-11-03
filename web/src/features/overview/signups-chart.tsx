"use client";

import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { Skeleton } from "@/components/ui/skeleton";
import { formatShortDate } from "@/lib/format";
import { Block } from "./block";
import { useOverviewStats } from "./queries";

const TICK = { fill: "var(--muted-foreground)", fontSize: 12 };

export function SignupsChart() {
  const query = useOverviewStats();
  return (
    <Block
      title="Sign-ups"
      description="Per week, last 12 weeks."
      query={query}
      skeleton={<Skeleton className="h-56 w-full" />}
    >
      {(data) => {
        const rows = data.signups.map((s) => ({ ...s, label: formatShortDate(s.week_start) }));
        const peak = rows.reduce((a, b) => (b.count > a.count ? b : a), rows[0]);
        const summary = peak
          ? `Sign-ups per week, last ${rows.length} weeks, peak ${peak.count} in week of ${peak.label}`
          : "No sign-ups in the last 12 weeks";
        return (
          <div role="img" aria-label={summary} className="h-56 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={rows} margin={{ top: 4, right: 4, bottom: 0, left: -20 }}>
                <CartesianGrid vertical={false} stroke="var(--border)" />
                <XAxis
                  dataKey="label"
                  tick={TICK}
                  tickLine={false}
                  axisLine={{ stroke: "var(--border)" }}
                  interval="preserveStartEnd"
                  minTickGap={16}
                />
                <YAxis tick={TICK} tickLine={false} axisLine={false} allowDecimals={false} />
                <Tooltip
                  cursor={{ fill: "var(--muted)", opacity: 0.5 }}
                  labelFormatter={(l) => `Week of ${l}`}
                  formatter={(v) => [v, "Sign-ups"]}
                  contentStyle={{
                    background: "var(--popover)",
                    color: "var(--popover-foreground)",
                    border: "1px solid var(--border)",
                    borderRadius: 8,
                    fontSize: 12,
                  }}
                  labelStyle={{ color: "var(--popover-foreground)" }}
                  itemStyle={{ color: "var(--popover-foreground)" }}
                />
                <Bar dataKey="count" fill="var(--chart-1)" radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        );
      }}
    </Block>
  );
}
