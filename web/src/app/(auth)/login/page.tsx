import { Suspense } from "react";

import { LoginForm, LoginPanel } from "@/features/auth/login-form";

export default function LoginPage() {
  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      <LoginPanel />
      <main id="content" className="flex items-center justify-center p-4 sm:p-8">
        <Suspense fallback={null}>
          <LoginForm />
        </Suspense>
      </main>
    </div>
  );
}
