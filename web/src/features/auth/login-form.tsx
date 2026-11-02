"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import {
  Activity,
  CircleAlert,
  Eye,
  EyeOff,
  Info,
  Loader2,
  ShieldCheck,
  ShieldHalf,
  UserCog,
  LineChart,
  type LucideIcon,
} from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError } from "@/lib/api-client";
import { useAuth } from "./auth-provider";
import { safeNext } from "./redirect";

const schema = z.object({
  email: z.email({ error: "Enter a valid work email" }),
  password: z.string().min(1, { error: "Enter your password" }),
});
type FormValues = z.infer<typeof schema>;

const DEMOS: {
  label: string;
  email: string;
  password: string;
  blurb: string;
  icon: LucideIcon;
}[] = [
  {
    label: "Ops admin",
    email: "admin@credisure.demo",
    password: "Admin@2026",
    blurb: "Full access, including re-running checks and simulating provider outages.",
    icon: UserCog,
  },
  {
    label: "Credit analyst",
    email: "analyst@credisure.demo",
    password: "Analyst@2026",
    blurb: "Browse businesses and the team. Cannot re-run checks.",
    icon: LineChart,
  },
  {
    label: "Viewer",
    email: "viewer@credisure.demo",
    password: "Viewer@2026",
    blurb: "Overview and provider health only.",
    icon: Eye,
  },
];

export function LoginPanel() {
  return (
    <div className="bg-primary text-primary-foreground hidden flex-col justify-between p-12 lg:flex">
      <div className="flex items-center gap-2 text-lg font-semibold">
        <ShieldHalf className="size-6" aria-hidden="true" />
        CrediSure
      </div>
      <div className="max-w-md space-y-8">
        <div className="space-y-3">
          <h1 className="text-3xl font-semibold tracking-tight">CrediSure Ops Console</h1>
          <p className="text-primary-foreground/80 text-lg">
            See which businesses are stuck in onboarding, why, and whether it&apos;s us or a
            provider.
          </p>
        </div>
        <ul className="text-primary-foreground/90 space-y-4 text-sm">
          <li className="flex items-center gap-3">
            <ShieldCheck className="size-5 shrink-0" aria-hidden="true" />4 verification checks
            tracked per business
          </li>
          <li className="flex items-center gap-3">
            <Activity className="size-5 shrink-0" aria-hidden="true" />
            Provider health checked every 15 s
          </li>
          <li className="flex items-center gap-3">
            <UserCog className="size-5 shrink-0" aria-hidden="true" />
            Role-based access for ops, analysts and viewers
          </li>
        </ul>
      </div>
      <p className="text-primary-foreground/60 text-xs">Internal tool</p>
    </div>
  );
}

export function LoginForm() {
  const router = useRouter();
  const params = useSearchParams();
  const { status, login } = useAuth();
  const reason = params.get("reason");
  const next = safeNext(params.get("next"));

  const [showPassword, setShowPassword] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    setValue,
    setError,
    setFocus,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { email: "", password: "" },
    shouldFocusError: true,
  });

  useEffect(() => {
    if (status === "authenticated") router.replace(next);
  }, [status, next, router]);

  async function onSubmit(values: FormValues) {
    setServerError(null);
    try {
      await login(values.email, values.password);
      router.replace(next);
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 401) {
          setServerError("Email or password is incorrect.");
        } else if (err.status === 422 && Array.isArray(err.details)) {
          let mapped = false;
          for (const d of err.details as { field?: string; message?: string }[]) {
            const name = d.field?.split(".").pop();
            if ((name === "email" || name === "password") && d.message) {
              setError(name, { message: d.message });
              mapped = true;
            }
          }
          if (!mapped) setServerError(err.message);
        } else {
          setServerError(err.message);
        }
      } else {
        setServerError("Something went wrong. Try again.");
      }
    }
  }

  function fillDemo(email: string, password: string) {
    setValue("email", email, { shouldValidate: true });
    setValue("password", password, { shouldValidate: true });
    setServerError(null);
    setFocus("password");
  }

  const banner =
    reason === "expired"
      ? "Your session expired. Sign in again."
      : reason === "signin"
        ? "Sign in to continue."
        : null;

  return (
    <Card className="w-full max-w-md">
      <CardHeader>
        <CardTitle className="text-xl">Sign in</CardTitle>
        <CardDescription>Use your CrediSure staff account.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-5">
        {banner && (
          <div
            role="status"
            className="border-info/30 bg-info/10 text-info flex items-start gap-2 rounded-lg border p-3 text-sm"
          >
            <Info className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
            {banner}
          </div>
        )}
        {serverError && (
          <div
            role="alert"
            className="border-danger/30 bg-danger/10 text-danger flex items-start gap-2 rounded-lg border p-3 text-sm"
          >
            <CircleAlert className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
            {serverError}
          </div>
        )}

        <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="email">Email</Label>
            <Input
              id="email"
              type="email"
              autoComplete="username"
              aria-invalid={errors.email ? true : undefined}
              aria-describedby={errors.email ? "email-error" : undefined}
              {...register("email")}
            />
            {errors.email && (
              <p id="email-error" className="text-danger text-sm">
                {errors.email.message}
              </p>
            )}
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="password">Password</Label>
            <div className="relative">
              <Input
                id="password"
                type={showPassword ? "text" : "password"}
                autoComplete="current-password"
                className="pr-10"
                aria-invalid={errors.password ? true : undefined}
                aria-describedby={errors.password ? "password-error" : undefined}
                {...register("password")}
              />
              <Button
                type="button"
                variant="ghost"
                size="icon-sm"
                className="absolute top-1/2 right-1 -translate-y-1/2"
                aria-pressed={showPassword}
                aria-label={showPassword ? "Hide password" : "Show password"}
                onClick={() => setShowPassword((v) => !v)}
              >
                {showPassword ? <EyeOff aria-hidden="true" /> : <Eye aria-hidden="true" />}
              </Button>
            </div>
            {errors.password && (
              <p id="password-error" className="text-danger text-sm">
                {errors.password.message}
              </p>
            )}
          </div>
          <Button type="submit" size="lg" className="w-full" disabled={isSubmitting}>
            {isSubmitting && <Loader2 className="animate-spin" aria-hidden="true" />}
            {isSubmitting ? "Signing in…" : "Sign in"}
          </Button>
        </form>

        <section aria-labelledby="demo-heading" className="space-y-2 border-t pt-4">
          <h2 id="demo-heading" className="text-muted-foreground text-sm font-medium">
            Demo accounts
          </h2>
          <ul className="space-y-2">
            {DEMOS.map((d) => (
              <li key={d.email}>
                <Button
                  type="button"
                  variant="outline"
                  className="h-auto w-full items-start justify-start gap-3 px-3 py-2 text-left whitespace-normal"
                  onClick={() => fillDemo(d.email, d.password)}
                >
                  <d.icon className="mt-0.5 size-4" aria-hidden="true" />
                  <span className="space-y-0.5">
                    <span className="block text-sm font-medium">{d.label}</span>
                    <span className="text-muted-foreground block text-xs font-normal">
                      {d.blurb}
                    </span>
                  </span>
                </Button>
              </li>
            ))}
          </ul>
        </section>

        <p className="text-muted-foreground text-xs">
          Prototype for CrediSure&apos;s engineering assessment. All data is fictional.
        </p>
      </CardContent>
    </Card>
  );
}
