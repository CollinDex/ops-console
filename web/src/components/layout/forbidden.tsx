"use client";

import { ShieldAlert } from "lucide-react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { useAuth } from "@/features/auth/auth-provider";
import { ROLE_LABEL } from "@/features/auth/types";

export function Forbidden({ feature }: { feature: string }) {
  const { user } = useAuth();
  const role = user ? ROLE_LABEL[user.role] : "current";
  return (
    <div
      role="alert"
      className="mx-auto flex max-w-md flex-col items-center gap-3 py-16 text-center"
    >
      <ShieldAlert className="text-warning size-10" aria-hidden="true" />
      <h2 className="text-lg font-semibold">
        Your role ({role}) can&apos;t view {feature}.
      </h2>
      <p className="text-muted-foreground text-sm">Ask an ops admin if you need access.</p>
      <Button asChild variant="outline">
        <Link href="/overview">Back to Overview</Link>
      </Button>
    </div>
  );
}
