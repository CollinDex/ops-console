import type { components } from "@/lib/api-types";

export type Me = components["schemas"]["UserOut"];
export type Role = components["schemas"]["Role"];
export type LoginResponse = components["schemas"]["LoginResponse"];

export const ROLE_LABEL: Record<Role, string> = {
  ops_admin: "Ops admin",
  analyst: "Credit analyst",
  viewer: "Viewer",
};
