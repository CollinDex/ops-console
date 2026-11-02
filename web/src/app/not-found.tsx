import { Compass } from "lucide-react";
import Link from "next/link";

import { Button } from "@/components/ui/button";

export default function NotFound() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-3 p-6 text-center">
      <Compass className="text-muted-foreground size-10" aria-hidden="true" />
      <h1 className="text-xl font-semibold">Page not found</h1>
      <p className="text-muted-foreground text-sm">That page doesn&apos;t exist or has moved.</p>
      <Button asChild>
        <Link href="/overview">Go to Overview</Link>
      </Button>
    </main>
  );
}
