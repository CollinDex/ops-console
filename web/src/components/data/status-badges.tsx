import {
  CircleCheck,
  CircleHelp,
  CircleX,
  Clock,
  TriangleAlert,
  type LucideIcon,
} from "lucide-react";

import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import type { components } from "@/lib/api-types";
import { cn } from "@/lib/utils";

export type CheckStatus = components["schemas"]["CheckStatus"];
export type CheckType = components["schemas"]["CheckType"];

export const CHECK_ORDER: CheckType[] = ["cac", "tin", "bvn", "bank_link"];
export const CHECK_SHORT: Record<CheckType, string> = {
  cac: "CAC",
  tin: "TIN",
  bvn: "BVN",
  bank_link: "Bank",
};
export const CHECK_LABEL: Record<CheckType, string> = {
  cac: "CAC",
  tin: "Tax ID",
  bvn: "BVN",
  bank_link: "Bank link",
};

export const STATUS_META: Record<
  CheckStatus,
  { label: string; icon: LucideIcon; text: string; bg: string }
> = {
  passed: { label: "Passed", icon: CircleCheck, text: "text-success", bg: "bg-success/10" },
  failed: { label: "Failed", icon: CircleX, text: "text-danger", bg: "bg-danger/10" },
  pending: { label: "Pending", icon: Clock, text: "text-warning", bg: "bg-warning/10" },
};

/** Icon + text, never colour alone. */
export function StatusBadge({ status, className }: { status: CheckStatus; className?: string }) {
  const m = STATUS_META[status];
  const Icon = m.icon;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium",
        m.bg,
        m.text,
        className,
      )}
    >
      <Icon className="size-3.5" aria-hidden="true" />
      {m.label}
    </span>
  );
}

/** Compact: the check's short label with a status icon. The tooltip spells the status out. */
export function CheckBadge({ type, status }: { type: CheckType; status: CheckStatus }) {
  const m = STATUS_META[status];
  const Icon = m.icon;
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <span
          className={cn(
            "inline-flex items-center gap-0.5 rounded-md px-1.5 py-0.5 text-[11px] font-medium",
            m.bg,
            m.text,
          )}
        >
          <Icon className="size-3" aria-hidden="true" />
          {CHECK_SHORT[type]}
          <span className="sr-only"> check {m.label.toLowerCase()}</span>
        </span>
      </TooltipTrigger>
      <TooltipContent>
        {CHECK_LABEL[type]}: {m.label}
      </TooltipContent>
    </Tooltip>
  );
}

export type ProviderState = "up" | "slow" | "down" | "unknown";

const PROVIDER_META: Record<
  ProviderState,
  { label: string; icon: LucideIcon; text: string; bg: string }
> = {
  up: { label: "Up", icon: CircleCheck, text: "text-success", bg: "bg-success/10" },
  slow: { label: "Slow", icon: TriangleAlert, text: "text-warning", bg: "bg-warning/10" },
  down: { label: "Down", icon: CircleX, text: "text-danger", bg: "bg-danger/10" },
  unknown: { label: "Unknown", icon: CircleHelp, text: "text-muted-foreground", bg: "bg-muted" },
};

export function ProviderStatusBadge({ status }: { status: ProviderState }) {
  const m = PROVIDER_META[status];
  const Icon = m.icon;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium",
        m.bg,
        m.text,
      )}
    >
      <Icon className="size-3.5" aria-hidden="true" />
      {m.label}
    </span>
  );
}
