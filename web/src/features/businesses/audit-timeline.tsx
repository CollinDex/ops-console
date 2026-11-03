"use client";

import { Download, RotateCw, ScrollText } from "lucide-react";

import { CHECK_LABEL, type CheckType } from "@/components/data/status-badges";
import { EmptyState, ErrorState } from "@/components/data/states";
import { Skeleton } from "@/components/ui/skeleton";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { ROLE_LABEL } from "@/features/auth/types";
import { formatDateTime, formatRelative } from "@/lib/format";
import { useAudit, type AuditEntry } from "./queries";

function Sentence({ entry }: { entry: AuditEntry }) {
  const who = entry.actor ? (
    <>
      <strong>{entry.actor.full_name}</strong> ({ROLE_LABEL[entry.actor.role]})
    </>
  ) : (
    <strong>System</strong>
  );
  if (entry.action === "check.retry") {
    const d = entry.details as {
      check?: CheckType;
      result?: string;
      failure_reason?: string | null;
    };
    const check = d.check ? CHECK_LABEL[d.check] : "a";
    return (
      <>
        {who} re-ran the {check} check: {d.result ?? "done"}
        {d.result === "failed" && d.failure_reason ? `, ${d.failure_reason}` : ""}
      </>
    );
  }
  return (
    <>
      {who} performed <span className="font-mono text-xs">{entry.action}</span>
    </>
  );
}

export function AuditTimeline({ businessId }: { businessId: string }) {
  const query = useAudit(businessId);

  if (query.isPending)
    return (
      <div className="space-y-3">
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-10 w-full" />
      </div>
    );
  if (query.isError)
    return <ErrorState compact error={query.error} onRetry={() => void query.refetch()} />;
  if (query.data.length === 0)
    return <EmptyState compact icon={ScrollText} title="No staff activity yet." />;

  return (
    <ol className="space-y-3">
      {query.data.map((e) => {
        const Icon = e.action === "check.retry" ? RotateCw : Download;
        return (
          <li key={e.id} className="flex gap-3 text-sm">
            <span className="bg-muted text-muted-foreground mt-0.5 flex size-6 shrink-0 items-center justify-center rounded-full">
              <Icon className="size-3" aria-hidden="true" />
            </span>
            <div className="min-w-0">
              <p>
                <Sentence entry={e} />
              </p>
              <Tooltip>
                <TooltipTrigger asChild>
                  <time dateTime={e.created_at} className="text-muted-foreground text-xs">
                    {formatRelative(e.created_at)}
                  </time>
                </TooltipTrigger>
                <TooltipContent>{formatDateTime(e.created_at)}</TooltipContent>
              </Tooltip>
            </div>
          </li>
        );
      })}
    </ol>
  );
}
