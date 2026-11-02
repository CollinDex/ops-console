const TOKEN_KEY = "credisure.token";
const EXP_KEY = "credisure.token_exp";

export const tokenStore = {
  get(): { token: string; expiresAt: string } | null {
    try {
      const token = window.localStorage.getItem(TOKEN_KEY);
      const expiresAt = window.localStorage.getItem(EXP_KEY);
      return token && expiresAt ? { token, expiresAt } : null;
    } catch {
      return null;
    }
  },
  getToken(): string | null {
    return this.get()?.token ?? null;
  },
  set(token: string, expiresAt: string): void {
    try {
      window.localStorage.setItem(TOKEN_KEY, token);
      window.localStorage.setItem(EXP_KEY, expiresAt);
    } catch {
      // Storage unavailable (private mode): the session just won't survive a reload.
    }
  },
  clear(): void {
    try {
      window.localStorage.removeItem(TOKEN_KEY);
      window.localStorage.removeItem(EXP_KEY);
    } catch {
      // ignore
    }
  },
};
