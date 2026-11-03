"use client";

import { Search, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import {
  InputGroup,
  InputGroupAddon,
  InputGroupButton,
  InputGroupInput,
} from "@/components/ui/input-group";
import { useDebouncedValue } from "@/lib/use-debounced-value";
import { cn } from "@/lib/utils";

/**
 * Local state is debounced before it reaches the URL (`onCommit`), and re-syncs whenever the URL
 * value changes from outside (back button, Clear all).
 */
export function SearchInput({
  value,
  onCommit,
  placeholder,
  label,
  className,
}: {
  value: string;
  onCommit: (value: string) => void;
  placeholder: string;
  label: string;
  className?: string;
}) {
  const [text, setText] = useState(value);
  const debounced = useDebouncedValue(text, 300);
  const committed = useRef(value);

  // URL -> input
  useEffect(() => {
    if (value !== committed.current) {
      committed.current = value;
      setText(value);
    }
  }, [value]);

  // input -> URL
  useEffect(() => {
    const next = debounced.trim();
    if (next !== committed.current) {
      committed.current = next;
      onCommit(next);
    }
  }, [debounced, onCommit]);

  return (
    <InputGroup className={cn("w-full sm:max-w-xs", className)}>
      <InputGroupAddon>
        <Search aria-hidden="true" />
      </InputGroupAddon>
      <InputGroupInput
        type="search"
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder={placeholder}
        aria-label={label}
        maxLength={100}
        className="[&::-webkit-search-cancel-button]:hidden"
      />
      {text && (
        <InputGroupAddon align="inline-end">
          <InputGroupButton
            size="icon-xs"
            aria-label="Clear search"
            onClick={() => {
              setText("");
              committed.current = "";
              onCommit("");
            }}
          >
            <X aria-hidden="true" />
          </InputGroupButton>
        </InputGroupAddon>
      )}
    </InputGroup>
  );
}
