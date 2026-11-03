import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { BAND_STYLE, bandFor } from "@/lib/score";
import { cn } from "@/lib/utils";

export function ScorePill({ score, className }: { score: number | null; className?: string }) {
  if (score === null) {
    return (
      <span className="text-muted-foreground">
        <span aria-hidden="true">—</span>
        <span className="sr-only">No score</span>
      </span>
    );
  }
  const band = bandFor(score);
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <span
          className={cn(
            "inline-flex items-center rounded-md px-1.5 py-0.5 font-mono text-xs font-medium tabular-nums",
            BAND_STYLE[band.key],
            className,
          )}
        >
          {score}
          <span className="sr-only"> ({band.label})</span>
        </span>
      </TooltipTrigger>
      <TooltipContent>
        {band.label} ({band.min}–{band.max})
      </TooltipContent>
    </Tooltip>
  );
}
