// Helpers de autenticação — armazenamento e leitura de tokens JWT.
// Todos os acessos a localStorage são guardados com try/catch para
// evitar crashes em ambientes SSR (Next.js roda código no servidor também).

import type { UserResponse } from "@/lib/types";

const ACCESS_TOKEN_KEY = "nexusai_access_token";
const REFRESH_TOKEN_KEY = "nexusai_refresh_token";
const TENANT_SLUG_KEY = "nexusai_tenant_slug";
const USER_KEY = "nexusai_user";

// ── Persistência ─────────────────────────────────────────────────────────────

export function saveTokens(
  accessToken: string,
  slug: string,
  user: UserResponse,
  refreshToken?: string // opcional — vai em httpOnly cookie, só persiste se fornecido
): void {
  try {
    localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
    localStorage.setItem(TENANT_SLUG_KEY, slug);
    localStorage.setItem(USER_KEY, JSON.stringify(user));
    if (refreshToken) {
      localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
    }
  } catch {
    // localStorage indisponível (SSR ou modo privado restrito)
  }
}

export function clearTokens(): void {
  try {
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
    localStorage.removeItem(TENANT_SLUG_KEY);
    localStorage.removeItem(USER_KEY);
  } catch {
    // localStorage indisponível
  }
}

// ── Leitura ───────────────────────────────────────────────────────────────────

export function getAccessToken(): string | null {
  try {
    return localStorage.getItem(ACCESS_TOKEN_KEY);
  } catch {
    return null;
  }
}

export function getRefreshToken(): string | null {
  try {
    return localStorage.getItem(REFRESH_TOKEN_KEY);
  } catch {
    return null;
  }
}

export function getTenantSlug(): string | null {
  try {
    return localStorage.getItem(TENANT_SLUG_KEY);
  } catch {
    return null;
  }
}

export function getStoredUser(): UserResponse | null {
  try {
    const raw = localStorage.getItem(USER_KEY);
    if (!raw) return null;
    return JSON.parse(raw) as UserResponse;
  } catch {
    return null;
  }
}

// ── Validação ─────────────────────────────────────────────────────────────────

export function isAuthenticated(): boolean {
  const token = getAccessToken();
  if (!token) return false;
  return !isTokenExpired(token);
}

export function isTokenExpired(token: string): boolean {
  try {
    const payload = token.split(".")[1];
    if (!payload) return true;
    const decoded = JSON.parse(atob(payload.replace(/-/g, "+").replace(/_/g, "/")));
    if (typeof decoded.exp !== "number") return true;
    return decoded.exp * 1000 < Date.now();
  } catch {
    return true;
  }
}
