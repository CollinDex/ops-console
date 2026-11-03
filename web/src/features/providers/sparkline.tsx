import type { ProviderStatus } from "./queries";

const W = 160;
const H = 36;
const PAD = 3;

type Point = ProviderStatus["recent"][number];

/** Latency over the recent pings. Down pings have no latency, so they become red ticks on the baseline. */
export function Sparkline({ points, current }: { points: Point[]; current: number | null }) {
  const label =
    points.length === 0
      ? "No latency data yet"
      : `Latency over the last ${Math.max(1, Math.round((points.length * 15) / 60))} minutes, ${
          current === null ? "currently down" : `currently ${current} ms`
        }`;
  if (points.length === 0) {
    return (
      <svg role="img" aria-label={label} viewBox={`0 0 ${W} ${H}`} className="h-9 w-40">
        <line
          x1={PAD}
          x2={W - PAD}
          y1={H - PAD}
          y2={H - PAD}
          stroke="var(--border)"
          strokeWidth={1}
        />
      </svg>
    );
  }
  const latencies = points.map((p) => p.latency_ms).filter((v): v is number => v !== null);
  const max = Math.max(1, ...latencies);
  const step = points.length > 1 ? (W - PAD * 2) / (points.length - 1) : 0;
  const x = (i: number) => PAD + i * step;
  const y = (v: number) => H - PAD - (v / max) * (H - PAD * 2 - 2);

  // Draw the line in runs so it breaks at down pings instead of diving to zero.
  const runs: { i: number; v: number }[][] = [];
  let run: { i: number; v: number }[] = [];
  points.forEach((p, i) => {
    if (p.status === "down" || p.latency_ms === null) {
      if (run.length) runs.push(run);
      run = [];
    } else {
      run.push({ i, v: p.latency_ms });
    }
  });
  if (run.length) runs.push(run);

  const lastIdx = points.length - 1;
  const last = points[lastIdx];
  return (
    <svg role="img" aria-label={label} viewBox={`0 0 ${W} ${H}`} className="h-9 w-40">
      <line
        x1={PAD}
        x2={W - PAD}
        y1={H - PAD}
        y2={H - PAD}
        stroke="var(--border)"
        strokeWidth={1}
      />
      {runs.map((r, k) => {
        const line = r.map((p, j) => `${j === 0 ? "M" : "L"}${x(p.i)},${y(p.v)}`).join(" ");
        const area = `${line} L${x(r[r.length - 1].i)},${H - PAD} L${x(r[0].i)},${H - PAD} Z`;
        return (
          <g key={k}>
            <path d={area} fill="var(--chart-1)" fillOpacity={0.12} />
            <path
              d={line}
              fill="none"
              stroke="var(--chart-1)"
              strokeWidth={1.5}
              strokeLinejoin="round"
              strokeLinecap="round"
            />
          </g>
        );
      })}
      {points.map((p, i) =>
        p.status === "down" || p.latency_ms === null ? (
          <line
            key={i}
            x1={x(i)}
            x2={x(i)}
            y1={H - PAD - 9}
            y2={H - PAD}
            stroke="var(--danger)"
            strokeWidth={2}
            strokeLinecap="round"
          />
        ) : null,
      )}
      {last.latency_ms !== null && last.status !== "down" && (
        <circle
          cx={x(lastIdx)}
          cy={y(last.latency_ms)}
          r={3}
          fill="var(--chart-1)"
          stroke="var(--card)"
          strokeWidth={1.5}
        />
      )}
    </svg>
  );
}
