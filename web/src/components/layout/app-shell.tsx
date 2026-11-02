import { AppSidebar } from "./app-sidebar";
import { Header } from "./header";

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen">
      <a
        href="#content"
        className="bg-primary text-primary-foreground focus-visible:ring-ring sr-only z-[60] rounded-md px-3 py-2 text-sm font-medium focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus-visible:ring-2"
      >
        Skip to content
      </a>
      <AppSidebar />
      <div className="lg:pl-60">
        <Header />
        <main id="content" tabIndex={-1} className="p-4 outline-none sm:p-6">
          {children}
        </main>
      </div>
    </div>
  );
}

export function ShellSkeleton() {
  return (
    <div className="min-h-screen" aria-busy="true" aria-label="Loading">
      <div className="bg-sidebar fixed inset-y-0 left-0 hidden w-60 border-r lg:block" />
      <div className="lg:pl-60">
        <div className="h-14 border-b" />
        <div className="space-y-4 p-6">
          <div className="bg-muted h-8 w-48 animate-pulse rounded-md" />
          <div className="bg-muted h-32 max-w-xl animate-pulse rounded-lg" />
        </div>
      </div>
    </div>
  );
}
