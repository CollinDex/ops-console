"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import { api, setUnauthorizedHandler } from "@/lib/api-client";
import { tokenStore } from "./token-store";
import type { LoginResponse, Me, Role } from "./types";

type AuthStatus = "loading" | "authenticated" | "anonymous";
type LogoutReason = "expired" | "signin";

type AuthContextValue = {
  status: AuthStatus;
  user: Me | null;
  /** True once logout() has already navigated to /login, so route guards must not redirect again. */
  redirecting: boolean;
  login: (email: string, password: string) => Promise<Me>;
  logout: (reason?: LogoutReason) => void;
  hasRole: (...roles: Role[]) => boolean;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [state, setState] = useState<{
    status: AuthStatus;
    user: Me | null;
    redirecting: boolean;
  }>({ status: "loading", user: null, redirecting: false });
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const clearTimer = useCallback(() => {
    if (timer.current) clearTimeout(timer.current);
    timer.current = null;
  }, []);

  const logout = useCallback(
    (reason?: LogoutReason) => {
      clearTimer();
      tokenStore.clear();
      queryClient.clear();
      setState({ status: "anonymous", user: null, redirecting: true });
      router.replace("/login" + (reason ? `?reason=${reason}` : ""));
    },
    [clearTimer, queryClient, router],
  );

  const scheduleExpiry = useCallback(
    (expiresAt: string) => {
      clearTimer();
      const ms = new Date(expiresAt).getTime() - Date.now();
      timer.current = setTimeout(() => logout("expired"), Math.max(0, Math.min(ms, 2 ** 31 - 1)));
    },
    [clearTimer, logout],
  );

  // Single place a 401 turns into a logout.
  useEffect(() => {
    setUnauthorizedHandler((code) => logout(code === "token_expired" ? "expired" : "signin"));
    return () => setUnauthorizedHandler(null);
  }, [logout]);

  // Restore the session on mount.
  useEffect(() => {
    const stored = tokenStore.get();
    if (!stored || new Date(stored.expiresAt).getTime() <= Date.now()) {
      tokenStore.clear();
      setState({ status: "anonymous", user: null, redirecting: false });
      return;
    }
    let cancelled = false;
    api<Me>("/auth/me")
      .then((user) => {
        if (cancelled) return;
        setState({ status: "authenticated", user, redirecting: false });
        scheduleExpiry(stored.expiresAt);
      })
      .catch(() => {
        // A 401 is handled by the api-client hook. Anything else leaves us signed out.
        if (cancelled) return;
        tokenStore.clear();
        setState({ status: "anonymous", user: null, redirecting: false });
      });
    return () => {
      cancelled = true;
      clearTimer();
    };
  }, [scheduleExpiry, clearTimer]);

  const login = useCallback(
    async (email: string, password: string) => {
      const res = await api<LoginResponse>("/auth/login", { body: { email, password } });
      tokenStore.set(res.access_token, res.expires_at);
      setState({ status: "authenticated", user: res.user, redirecting: false });
      scheduleExpiry(res.expires_at);
      return res.user;
    },
    [scheduleExpiry],
  );

  const value = useMemo<AuthContextValue>(
    () => ({
      ...state,
      login,
      logout,
      hasRole: (...roles) => state.user !== null && roles.includes(state.user.role),
    }),
    [state, login, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
