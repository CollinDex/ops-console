import { ShieldHalf } from "lucide-react";

export function Brand() {
  return (
    <div className="text-primary flex items-center gap-2 font-semibold">
      <ShieldHalf className="size-5" aria-hidden="true" />
      <span>CrediSure</span>
      <span className="text-muted-foreground text-xs font-medium">Ops</span>
    </div>
  );
}
