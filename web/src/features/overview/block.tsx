"use client";

import type { UseQueryResult } from "@tanstack/react-query";

import { ErrorState } from "@/components/data/states";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

/** A titled card that owns its loading and error state, so one failure never blanks the page. */
export function Block<T>({
  title,
  description,
  query,
  skeleton,
  children,
  action,
  className,
}: {
  title: string;
  description?: string;
  query: UseQueryResult<T>;
  skeleton: React.ReactNode;
  children: (data: T) => React.ReactNode;
  action?: React.ReactNode;
  className?: string;
}) {
  return (
    <Card className={cn("gap-3", className)}>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        {description && <CardDescription>{description}</CardDescription>}
        {action}
      </CardHeader>
      <CardContent>
        {query.data !== undefined ? (
          children(query.data)
        ) : query.isError ? (
          <ErrorState
            compact
            error={query.error}
            retrying={query.isFetching}
            onRetry={() => void query.refetch()}
          />
        ) : (
          skeleton
        )}
      </CardContent>
    </Card>
  );
}
