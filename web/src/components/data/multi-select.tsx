"use client";

import { ChevronDown } from "lucide-react";
import { useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";

export type Option = { value: string; label: string };

export function MultiSelect({
  label,
  options,
  selected,
  onChange,
  searchable = false,
}: {
  label: string;
  options: Option[];
  selected: string[];
  onChange: (values: string[]) => void;
  searchable?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const listRef = useRef<HTMLDivElement>(null);
  const toggle = (value: string) =>
    onChange(selected.includes(value) ? selected.filter((v) => v !== value) : [...selected, value]);

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button variant="outline" aria-label={`${label} filter`}>
          {label}
          {selected.length > 0 && (
            <span className="text-primary font-semibold">· {selected.length}</span>
          )}
          <ChevronDown className="text-muted-foreground" aria-hidden="true" />
        </Button>
      </PopoverTrigger>
      <PopoverContent
        align="start"
        className="w-60 p-0"
        onOpenAutoFocus={(e) => {
          // Without a search box, focus the list itself so arrow keys and Enter reach cmdk.
          if (!searchable) {
            e.preventDefault();
            listRef.current?.focus();
          }
        }}
      >
        <Command ref={listRef} tabIndex={-1} className="outline-none">
          {searchable && <CommandInput placeholder={`Search ${label.toLowerCase()}`} />}
          <CommandList>
            <CommandEmpty>No matches.</CommandEmpty>
            <CommandGroup>
              {options.map((o) => {
                const checked = selected.includes(o.value);
                return (
                  <CommandItem key={o.value} value={o.label} onSelect={() => toggle(o.value)}>
                    <Checkbox checked={checked} tabIndex={-1} aria-hidden="true" />
                    {o.label}
                    {checked && <span className="sr-only"> (selected)</span>}
                  </CommandItem>
                );
              })}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}
