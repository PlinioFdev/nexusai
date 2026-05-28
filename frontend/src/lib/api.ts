// Fetch wrapper centralizado.
// - Injeta Authorization header automaticamente
// - Redireciona para /login em caso de 401
// - Lança ApiError com status e mensagem estruturada para tratamento nos hooks

import { getAccessToken, clearTokens } from "@/lib/auth";

// ── Erro tipado ───────────────────────────────────────────────────────────────

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string
  ) {
    super(message);
    this.name = "ApiError";
  }
}

// ── Config ────────────────────────────────────────────────────────────────────

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// ── Core ──────────────────────────────────────────────────────────────────────

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getAccessToken();

  const headers: Record<string, string> = {
    ...(options.body && !(options.body instanceof FormData)
      ? { "Content-Type": "application/json" }
      : {}),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(options.headers as Record<string, string> | undefined),
  };

  const response = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers,
  });

  if (response.status === 401) {
    clearTokens();
    // Redireciona apenas no browser — não no SSR
    if (typeof window !== "undefined") {
      window.location.href = "/login";
    }
    throw new ApiError(401, "Sessão expirada");
  }

  if (!response.ok) {
    let message = `Erro ${response.status}`;
    try {
      const body = await response.json();
      message = body.detail ?? message;
    } catch {
      // body não é JSON — mantém mensagem padrão
    }
    throw new ApiError(response.status, message);
  }

  // 204 No Content — retorna null sem tentar parsear JSON
  if (response.status === 204) {
    return null as T;
  }

  return response.json() as Promise<T>;
}

// ── Métodos públicos ──────────────────────────────────────────────────────────

export const api = {
  get<T>(path: string): Promise<T> {
    return request<T>(path, { method: "GET" });
  },

  post<T>(path: string, body?: unknown): Promise<T> {
    return request<T>(path, {
      method: "POST",
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  },

  postForm<T>(path: string, formData: FormData): Promise<T> {
    return request<T>(path, {
      method: "POST",
      body: formData,
      // Content-Type NÃO é setado manualmente para multipart/form-data —
      // o browser precisa definir o boundary automaticamente
    });
  },

  delete<T>(path: string): Promise<T> {
    return request<T>(path, { method: "DELETE" });
  },
};
