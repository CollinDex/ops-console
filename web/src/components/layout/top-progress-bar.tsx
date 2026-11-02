"use client";

import { useIsFetching, useIsMutating } from "@tanstack/react-query";
import { useEffect, useState } from "react";

const SHOW_DELAY_MS = 150;

export function TopProgressBar() {
  // Background polls (meta.background) don't count, so the 30 s health check never shows the bar.
  const fetching = useIsFetching({ predicate: (q) => !q.meta?.background });
  const mutating = useIsMutating();
  const busy = fetching + mutating > 0;

  const [visible, setVisible] = useState(false);
  useEffect(() => {
    if (!busy) {
      setVisible(false);
      return;
    }
    const id = setTimeout(() => setVisible(true), SHOW_DELAY_MS);
    return () => clearTimeout(id);
  }, [busy]);

  return (
    <div
      role="progressbar"
      aria-label="Loading"
      aria-hidden={!visible}
      data-visible={visible}
      className="pointer-events-none fixed inset-x-0 top-0 z-50 h-0.5 overflow-hidden"
    >
      {visible && <div className="progress-indeterminate bg-primary h-full" />}
    </div>
  );
}
