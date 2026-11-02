import { MutationCache, QueryCache, QueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { ApiError } from "@/lib/api-client";

declare module "@tanstack/react-query" {
  interface Register {
    queryMeta: { silent?: boolean; background?: boolean };
    mutationMeta: { silent?: boolean };
  }
}

export function makeQueryClient(): QueryClient {
  return new QueryClient({
    queryCache: new QueryCache({
      onError(error, query) {
        if (query.meta?.silent) return;
        if (error instanceof ApiError && (error.status === 401 || error.status === 403)) return;
        const requestId = error instanceof ApiError ? error.requestId : undefined;
        toast.error(error.message, {
          id: JSON.stringify(query.queryKey),
          description: requestId ? `Ref ${requestId.slice(0, 8)}` : undefined,
          action: { label: "Retry", onClick: () => void query.fetch() },
        });
      },
    }),
    mutationCache: new MutationCache({
      onError(error, _variables, _context, mutation) {
        if (mutation.meta?.silent) return;
        toast.error(error.message);
      },
    }),
    defaultOptions: {
      queries: {
        staleTime: 30_000,
        refetchOnWindowFocus: true,
        retry: (failureCount, error) =>
          !(error instanceof ApiError && error.status >= 400 && error.status < 500) &&
          failureCount < 1,
      },
    },
  });
}
