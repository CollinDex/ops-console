"use client";

import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

type ApiState = "checking" | "ok" | "unreachable";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function Home() {
  const [state, setState] = useState<ApiState>("checking");

  useEffect(() => {
    const controller = new AbortController();
    fetch(`${API_URL}/health`, { signal: controller.signal })
      .then((res) => setState(res.ok ? "ok" : "unreachable"))
      .catch((err: unknown) => {
        if (!(err instanceof DOMException && err.name === "AbortError")) setState("unreachable");
      });
    return () => controller.abort();
  }, []);

  return (
    <main className="flex min-h-screen items-center justify-center p-6">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>CrediSure Ops Console: Phase 1 skeleton</CardTitle>
          <CardDescription>Placeholder page. Real screens arrive in later phases.</CardDescription>
        </CardHeader>
        <CardContent className="flex items-center gap-2">
          <span className="text-sm">API:</span>
          <Badge variant={state === "ok" ? "default" : "secondary"}>
            {state === "checking" ? "checking" : state}
          </Badge>
        </CardContent>
      </Card>
    </main>
  );
}
