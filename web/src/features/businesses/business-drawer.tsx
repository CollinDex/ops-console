"use client";

import { RotateCw, TriangleAlert } from "lucide-react";
import { useRef } from "react";

import { ScorePill } from "@/components/data/score-pill";
import { StageBadge } from "@/components/data/stage-badge";
import { ErrorState } from "@/components/data/states";
import { CHECK_LABEL, CHECK_ORDER, CheckBadge, STATUS_META } from "@/components/data/status-badges";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Skeleton } from "@/components/ui/skeleton";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { useAuth } from "@/features/auth/auth-provider";
import { ApiError } from "@/lib/api-client";
import { formatDate, formatDateTime, formatRelative } from "@/lib/format";
import { AuditTimeline } from "./audit-timeline";
import { useBusiness, useRetryCheck, type BusinessDetail } from "./queries";

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="space-y-3 px-4 py-4">
      <h3 className="text-muted-foreground text-xs font-semibold tracking-wide uppercase">
        {title}
      </h3>
      {children}
    </section>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-4 text-sm">
      <dt className="text-muted-foreground shrink-0">{label}</dt>
      <dd className="min-w-0 text-right">{children}</dd>
    </div>
  );
}

function ChecksSection({ business }: { business: BusinessDetail }) {
  const { hasRole } = useAuth();
  const { retry, isPending } = useRetryCheck(business.id);
  const isAdmin = hasRole("ops_admin");
  const byType = new Map(business.checks.map((c) => [c.type, c]));

  return (
    <ul className="space-y-3">
      {CHECK_ORDER.map((type) => {
        const check = byType.get(type);
        if (!check) return null;
        const pending = isPending(type);
        return (
          <li key={type} className="space-y-2 rounded-lg border p-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <CheckBadge type={type} status={check.status} />
                <span className="text-sm font-medium">{STATUS_META[check.status].label}</span>
              </div>
              {check.status === "failed" &&
                (isAdmin ? (
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={pending}
                    aria-label={`Re-run ${CHECK_LABEL[type]} check`}
                    onClick={() => retry(type)}
                  >
                    <RotateCw className={pending ? "animate-spin" : ""} aria-hidden="true" />
                    {pending ? "Re-running…" : "Re-run check"}
                  </Button>
                ) : (
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <span tabIndex={0} className="inline-flex rounded-md">
                        <Button
                          size="sm"
                          variant="outline"
                          disabled
                          aria-label={`Re-run ${CHECK_LABEL[type]} check (not permitted)`}
                        >
                          <RotateCw aria-hidden="true" />
                          Re-run check
                        </Button>
                      </span>
                    </TooltipTrigger>
                    <TooltipContent>Only ops admins can re-run checks</TooltipContent>
                  </Tooltip>
                ))}
            </div>
            <p className="text-muted-foreground flex flex-wrap gap-x-3 text-xs">
              <Tooltip>
                <TooltipTrigger asChild>
                  <span>Updated {formatRelative(check.updated_at)}</span>
                </TooltipTrigger>
                <TooltipContent>{formatDateTime(check.updated_at)}</TooltipContent>
              </Tooltip>
              <span>Attempts: {check.attempts}</span>
            </p>
            {check.status === "failed" && check.failure_reason && (
              <p className="bg-danger/10 text-danger rounded-md px-2.5 py-1.5 text-sm">
                {check.failure_reason}
              </p>
            )}
          </li>
        );
      })}
    </ul>
  );
}

function DrawerBody({ business }: { business: BusinessDetail }) {
  return (
    <div className="divide-y overflow-y-auto pb-6">
      <Section title="Verification checks">
        <ChecksSection business={business} />
      </Section>
      <Section title="Credit profile">
        <dl className="space-y-2">
          <Row label="Credit score">
            <ScorePill score={business.credit_score} />
          </Row>
          <Row label="Consent">
            {business.consent_given_at ? (
              `Given ${formatDate(business.consent_given_at)}`
            ) : (
              <span className="text-warning">Not given</span>
            )}
          </Row>
        </dl>
      </Section>
      <Section title="Bank data">
        <dl className="space-y-2">
          <Row label="Bank">{business.bank_name}</Row>
          <Row label="Account">
            <span className="font-mono">{business.account_masked}</span>
          </Row>
          <Row label="Last sync">
            {business.last_bank_sync_at ? (
              <span className="inline-flex flex-wrap items-center justify-end gap-2">
                {formatRelative(business.last_bank_sync_at)}
                {business.bank_data_stale && (
                  <span className="bg-warning/10 text-warning inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium">
                    <TriangleAlert className="size-3" aria-hidden="true" />
                    Stale
                  </span>
                )}
              </span>
            ) : (
              "—"
            )}
          </Row>
        </dl>
      </Section>
      <Section title="Identity">
        <dl className="space-y-2">
          <Row label="Director">{business.director_name}</Row>
          <Row label="BVN">
            <span className="font-mono">{business.bvn_masked}</span>
            <span className="text-muted-foreground block text-xs">Masked: last 4 digits only</span>
          </Row>
        </dl>
      </Section>
      <Section title="Activity">
        <AuditTimeline businessId={business.id} />
      </Section>
    </div>
  );
}

export function BusinessDrawer({ id, onClose }: { id: string | undefined; onClose: () => void }) {
  const query = useBusiness(id);
  // `id` is already gone from the URL by the time the close animation hands focus back.
  const lastId = useRef<string | undefined>(id);
  if (id) lastId.current = id;
  const notFound = query.error instanceof ApiError && query.error.status === 404;

  return (
    <Sheet open={!!id} onOpenChange={(open) => !open && onClose()}>
      <SheetContent
        className="w-full data-[side=right]:w-full data-[side=right]:sm:max-w-lg"
        onCloseAutoFocus={(e) => {
          // No trigger element, so hand focus back to the row that opened the drawer.
          const row = lastId.current
            ? document.querySelector<HTMLElement>(`[data-row-focus="${lastId.current}"]`)
            : null;
          if (row) {
            e.preventDefault();
            row.focus();
          }
        }}
      >
        <SheetHeader className="border-b pr-12">
          {query.data ? (
            <>
              <SheetTitle className="text-lg">{query.data.name}</SheetTitle>
              <div className="flex flex-wrap items-center gap-2 pt-1">
                <StageBadge stage={query.data.stage} />
              </div>
              <SheetDescription className="pt-1">
                <span className="font-mono">{query.data.cac_number}</span> ·{" "}
                <span className="capitalize">{query.data.sector}</span> · {query.data.state}
              </SheetDescription>
            </>
          ) : (
            <>
              <SheetTitle>{notFound ? "Business not found" : "Business details"}</SheetTitle>
              <SheetDescription className="sr-only">Business details</SheetDescription>
            </>
          )}
        </SheetHeader>
        {query.data ? (
          <DrawerBody business={query.data} />
        ) : notFound ? (
          <div className="flex flex-col items-center gap-3 px-4 py-12 text-center">
            <p className="text-muted-foreground text-sm">
              This business doesn&apos;t exist or the link is out of date.
            </p>
            <Button variant="outline" onClick={onClose}>
              Close
            </Button>
          </div>
        ) : query.isError ? (
          <ErrorState error={query.error} onRetry={() => void query.refetch()} />
        ) : (
          <div className="space-y-6 p-4">
            {Array.from({ length: 4 }, (_, i) => (
              <div key={i} className="space-y-2">
                <Skeleton className="h-4 w-32" />
                <Skeleton className="h-16 w-full" />
              </div>
            ))}
          </div>
        )}
      </SheetContent>
    </Sheet>
  );
}
