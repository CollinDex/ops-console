import { Brand } from "./brand";
import { NavLinks } from "./nav-links";

export function AppSidebar() {
  return (
    <aside className="bg-sidebar fixed inset-y-0 left-0 hidden w-60 flex-col border-r lg:flex">
      <div className="flex h-14 items-center border-b px-4">
        <Brand />
      </div>
      <NavLinks className="flex-1 overflow-y-auto p-3" />
      <div className="border-t p-4">
        <span className="bg-muted text-muted-foreground inline-flex items-center rounded-md px-2 py-1 text-xs font-medium">
          Demo data
        </span>
      </div>
    </aside>
  );
}
