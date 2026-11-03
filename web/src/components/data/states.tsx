"use client";

import { Inbox, RefreshCw, TriangleAlert } from "lucide-react";

import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api-client";
import { cn } from "@/lib/utils";

export function EmptyState({
  title,
  description,
  action,
  compact,
  icon: Icon = Inbox,
}: {
  title: string;
  description?: string;
  action?: React.ReactNode;
  compact?: boolean;
  icon?: React.ElementType;
}) {
  return (
    <div className={cn("flex flex-col items-center gap-2 text-center", compact ? "py-8" : "py-16")}>
      <Icon className="text-muted-foreground size-8" aria-hidden="true" />
      <p className="font-medium">{title}</p>
      {description && <p className="text-muted-foreground max-w-sm text-sm">{description}</p>}
      {action}
    </div>
  );
}

export function ErrorState({
  error,
  onRetry,
  compact,
  retrying,
}: {
  error: unknown;
  onRetry?: () => void;
  compact?: boolean;
  retrying?: boolean;
}) {
  const message = error instanceof Error ? error.message : "Something went wrong.";
  const ref = error instanceof ApiError ? error.requestId : undefined;
  return (
    <div
      role="alert"
      className={cn("flex flex-col items-center gap-2 text-center", compact ? "py-8" : "py-16")}
    >
      <TriangleAlert className="text-danger size-8" aria-hidden="true" />
      <p className="font-medium">{message}</p>
      {ref && <p className="text-muted-foreground font-mono text-xs">Ref {ref.slice(0, 8)}</p>}
      {onRetry && (
        <Button variant="outline" size="sm" onClick={onRetry} disabled={retrying}>
          <RefreshCw className={cn(retrying && "animate-spin")} aria-hidden="true" />
          Retry
        </Button>
      )}
    </div>
  );
}

export function isForbidden(error: unknown): boolean {
  return error instanceof ApiError && error.status === 403;
}
