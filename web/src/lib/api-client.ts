import { tokenStore } from "@/features/auth/token-store";

export class ApiError extends Error {
  status: number;
  code: string;
  requestId?: string;
  details?: unknown;

  constructor(
    status: number,
    code: string,
    message: string,
    opts: { requestId?: string; details?: unknown } = {},
  ) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.requestId = opts.requestId;
    this.details = opts.details;
  }
}

const NETWORK_MESSAGE = "Can't reach the CrediSure API. Check your connection and try again.";

type UnauthorizedHandler = (code: string) => void;
let unauthorizedHandler: UnauthorizedHandler | null = null;

/** The AuthProvider registers this once. It is the single place a 401 leads to logout. */
export function setUnauthorizedHandler(handler: UnauthorizedHandler | null): void {
  unauthorizedHandler = handler;
}

export type ApiInit = {
  method?: string;
  body?: unknown;
  headers?: Record<string, string>;
  signal?: AbortSignal;
};

function buildUrl(path: string): string {
  const base = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");
  const prefix = path.startsWith("/health") ? "" : "/api/v1";
  return `${base}${prefix}${path}`;
}

async function request(path: string, init: ApiInit = {}): Promise<Response> {
  const headers: Record<string, string> = { ...init.headers };
  const token = tokenStore.getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  const hasBody = init.body !== undefined;
  if (hasBody) headers["Content-Type"] = "application/json";

  let res: Response;
  try {
    res = await fetch(buildUrl(path), {
      method: init.method ?? (hasBody ? "POST" : "GET"),
      headers,
      body: hasBody ? JSON.stringify(init.body) : undefined,
      signal: init.signal,
    });
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") throw err;
    throw new ApiError(0, "network_error", NETWORK_MESSAGE);
  }

  if (res.ok) return res;

  let error: ApiError;
  try {
    const body: unknown = await res.json();
    const env = (body as { error?: Record<string, unknown> } | null)?.error;
    if (env && typeof env.code === "string" && typeof env.message === "string") {
      error = new ApiError(res.status, env.code, env.message, {
        requestId: typeof env.request_id === "string" ? env.request_id : undefined,
        details: env.details,
      });
    } else {
      error = new ApiError(res.status, "http_error", `Request failed (${res.status}).`);
    }
  } catch {
    error = new ApiError(res.status, "http_error", `Request failed (${res.status}).`);
  }

  if (res.status === 401 && path !== "/auth/login") unauthorizedHandler?.(error.code);
  throw error;
}

export async function api<T>(path: string, init?: ApiInit): Promise<T> {
  const res = await request(path, init);
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

/** For file downloads such as the CSV export (Phase 6). */
export async function apiBlob(path: string, init?: ApiInit): Promise<Blob> {
  const res = await request(path, init);
  return res.blob();
}

export type Download = { blob: Blob; filename: string | null; truncated: boolean };

/** A file download with the auth header. The filename comes from the server's Content-Disposition. */
export async function apiDownload(path: string, init?: ApiInit): Promise<Download> {
  const res = await request(path, init);
  const disposition = res.headers.get("Content-Disposition") ?? "";
  const match = /filename\*?=(?:UTF-8'')?"?([^";]+)"?/i.exec(disposition);
  return {
    blob: await res.blob(),
    filename: match ? decodeURIComponent(match[1]) : null,
    truncated: res.headers.get("X-Truncated") === "true",
  };
}
