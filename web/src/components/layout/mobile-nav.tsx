"use client";

import { Menu } from "lucide-react";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { Brand } from "./brand";
import { NavLinks } from "./nav-links";

export function MobileNav() {
  const [open, setOpen] = useState(false);
  const pathname = usePathname();

  useEffect(() => {
    setOpen(false);
  }, [pathname]);

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className="lg:hidden"
          aria-label="Open navigation"
          aria-expanded={open}
        >
          <Menu aria-hidden="true" />
        </Button>
      </SheetTrigger>
      <SheetContent side="left" className="w-64 gap-0 p-0">
        <SheetTitle className="sr-only">Navigation</SheetTitle>
        <SheetDescription className="sr-only">Main navigation links</SheetDescription>
        <div className="flex h-14 items-center border-b px-4">
          <Brand />
        </div>
        <NavLinks className="flex-1 p-3" />
        <div className="border-t p-4">
          <span className="bg-muted text-muted-foreground inline-flex items-center rounded-md px-2 py-1 text-xs font-medium">
            Demo data
          </span>
        </div>
      </SheetContent>
    </Sheet>
  );
}
