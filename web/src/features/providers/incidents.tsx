import { EmptyState, ErrorState } from "@/components/data/states";
import { ProviderStatusBadge } from "@/components/data/status-badges";
import { Skeleton } from "@/components/ui/skeleton";
import { formatDateTime, formatRelative } from "@/lib/format";
import { useProviderIncidents, type ProviderName } from "./queries";

function duration(seconds: number): string {
  if (seconds < 60) return `${seconds} s`;
  const min = Math.round(seconds / 60);
  if (min < 60) return `${min} min`;
  const h = Math.floor(min / 60);
  const m = min % 60;
  return m ? `${h} h ${m} min` : `${h} h`;
}

export function IncidentList({ name }: { name: ProviderName }) {
  const query = useProviderIncidents(name, true);
  if (query.isError)
    return (
      <ErrorState
        compact
        error={query.error}
        retrying={query.isFetching}
        onRetry={() => void query.refetch()}
      />
    );
  if (!query.data)
    return (
      <div className="space-y-2">
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-10 w-full" />
      </div>
    );
  if (query.data.length === 0)
    return <EmptyState compact title="No incidents in the last 7 days." />;
  return (
    <ul className="divide-y">
      {query.data.map((i) => (
        <li
          key={i.started_at}
          className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1 py-2 text-sm"
        >
          <span>
            <span className="block">{formatDateTime(i.started_at)}</span>
            <span className="text-muted-foreground text-xs">{formatRelative(i.started_at)}</span>
          </span>
          <span className="flex items-center gap-2">
            {i.ended_at === null && (
              <span className="bg-danger/10 text-danger rounded-full px-2 py-0.5 text-xs font-medium">
                Ongoing
              </span>
            )}
            <span className="text-muted-foreground font-mono text-xs tabular-nums">
              {duration(i.duration_seconds)}
            </span>
            <ProviderStatusBadge status={i.worst_status} />
          </span>
        </li>
      ))}
    </ul>
  );
}
