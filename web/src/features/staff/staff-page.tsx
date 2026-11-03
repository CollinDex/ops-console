"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { SearchX, Users } from "lucide-react";
import { useCallback, useRef } from "react";

import { DataTable, type Column } from "@/components/data/data-table";
import { MultiSelect } from "@/components/data/multi-select";
import { Pagination } from "@/components/data/pagination";
import { SearchInput } from "@/components/data/search-input";
import { EmptyState, ErrorState, isForbidden } from "@/components/data/states";
import { Forbidden } from "@/components/layout/forbidden";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ROLE_LABEL } from "@/features/auth/types";
import { api } from "@/lib/api-client";
import type { components } from "@/lib/api-types";
import { formatDate, initials } from "@/lib/format";
import { ROLES, STAFF_PAGE_SIZE, useStaffFilters, type StaffFilters } from "./filters";

type Staff = components["schemas"]["StaffOut"];
type StaffPage = components["schemas"]["Page_StaffOut_"];

const COLUMNS: Column<Staff>[] = [
  {
    id: "name",
    header: "Name",
    sortKey: "full_name",
    cell: (s) => (
      <div className="flex items-center gap-3">
        <Avatar size="sm">
          <AvatarFallback>{initials(s.full_name)}</AvatarFallback>
        </Avatar>
        <span className="font-medium">{s.full_name}</span>
      </div>
    ),
  },
  {
    id: "email",
    header: "Email",
    cell: (s) => <span className="font-mono text-xs">{s.email}</span>,
  },
  {
    id: "role",
    header: "Role",
    sortKey: "role",
    cell: (s) => <Badge variant="secondary">{ROLE_LABEL[s.role]}</Badge>,
  },
  {
    id: "joined",
    header: "Joined",
    sortKey: "created_at",
    defaultOrder: "desc",
    hideBelow: "md",
    cell: (s) => formatDate(s.created_at),
  },
];

const ROLE_OPTIONS = ROLES.map((r) => ({ value: r, label: ROLE_LABEL[r] }));

export function StaffPage() {
  const { filters, setFilters, clearAll } = useStaffFilters();
  const top = useRef<HTMLDivElement>(null);

  const query = useQuery({
    queryKey: ["staff", filters],
    queryFn: ({ signal }) => {
      const q = new URLSearchParams({
        sort: filters.sort,
        order: filters.order,
        page: String(filters.page),
        page_size: String(STAFF_PAGE_SIZE),
      });
      if (filters.search) q.set("search", filters.search);
      for (const r of filters.role) q.append("role", r);
      return api<StaffPage>(`/staff?${q}`, { signal });
    },
    placeholderData: keepPreviousData,
    meta: { silent: true },
  });

  const commitSearch = useCallback((search: string) => setFilters({ search }), [setFilters]);

  if (isForbidden(query.error)) return <Forbidden feature="Team" />;
  const data = query.data;
  const active = filters.search !== "" || filters.role.length > 0;

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-xl font-semibold">Team</h2>
        <p className="text-muted-foreground text-sm">Staff who can sign in to the Ops Console</p>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <SearchInput
          value={filters.search}
          onCommit={commitSearch}
          placeholder="Search name or email"
          label="Search team"
        />
        <MultiSelect
          label="Role"
          options={ROLE_OPTIONS}
          selected={filters.role}
          onChange={(role) => setFilters({ role: role as StaffFilters["role"] })}
        />
        {active && (
          <Button variant="ghost" size="sm" onClick={clearAll}>
            Clear all
          </Button>
        )}
      </div>
      <div ref={top} className="scroll-mt-20 space-y-3">
        {query.isError && !data ? (
          <ErrorState
            error={query.error}
            retrying={query.isFetching}
            onRetry={() => void query.refetch()}
          />
        ) : data && data.items.length === 0 ? (
          <EmptyState
            icon={active ? SearchX : Users}
            title="No team members match"
            action={
              <Button variant="outline" size="sm" onClick={clearAll}>
                Clear all
              </Button>
            }
          />
        ) : (
          <DataTable
            caption="Team"
            columns={COLUMNS}
            rows={data?.items ?? []}
            getRowId={(s) => s.id}
            sort={filters.sort}
            order={filters.order}
            onSortChange={(sort, order) =>
              setFilters({ sort: sort as StaffFilters["sort"], order })
            }
            loading={!data}
            refreshing={query.isFetching && !!data}
          />
        )}
        {data && data.total > 0 && (
          <Pagination
            page={data.page}
            pageSize={STAFF_PAGE_SIZE}
            total={data.total}
            onPageChange={(page) => {
              setFilters({ page });
              top.current?.scrollIntoView({ behavior: "smooth", block: "start" });
            }}
          />
        )}
      </div>
    </div>
  );
}
