import { Badge } from "@/components/ui/badge";
import type { components } from "@/lib/api-types";

export type Stage = components["schemas"]["Stage"];

/** Fallback labels, used until /meta/filters (or the overview funnel) supplies the server ones. */
export const STAGE_LABEL: Record<Stage, string> = {
  signed_up: "Signed up",
  documents_submitted: "Documents submitted",
  checks_in_progress: "Checks in progress",
  bank_linked: "Bank linked",
  profile_ready: "Profile ready",
};

export function StageBadge({ stage, label }: { stage: Stage; label?: string }) {
  return (
    <Badge variant="outline" className="font-normal">
      {label ?? STAGE_LABEL[stage]}
    </Badge>
  );
}
