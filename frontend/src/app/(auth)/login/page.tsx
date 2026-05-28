"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { api, ApiError } from "@/lib/api";
import { saveTokens, clearTokens } from "@/lib/auth";
import type { LoginRequest, TokenResponse, UserResponse } from "@/lib/types";

export default function LoginPage() {
  const router = useRouter();

  const [slug, setSlug] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setIsLoading(true);

    try {
      const body: LoginRequest = { slug, email, password };
      const tokens = await api.post<TokenResponse>("/api/v1/auth/login", body);

      // Salva access token para que api.get("/me") já injete o header
      saveTokens(tokens.access_token, slug, {
        id: "",
        email: "",
        role: "MEMBER",
        tenant_id: "",
        is_active: true,
        created_at: "",
        updated_at: "",
      });

      const user = await api.get<UserResponse>("/api/v1/auth/me");

      // Sobrescreve com dados reais do usuário
      saveTokens(tokens.access_token, slug, user);
      router.push("/documents");
    } catch (err) {
      clearTokens();
      if (err instanceof ApiError) {
        setError(
          err.status === 401
            ? "Credenciais inválidas. Verifique o workspace, email e senha."
            : err.message
        );
      }
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <h1 className="text-2xl font-bold text-gray-900">NexusAI</h1>
          <p className="mt-1 text-sm text-gray-500">
            Entre com seu workspace para continuar
          </p>
        </div>

        <form
          onSubmit={handleSubmit}
          className="flex flex-col gap-4 rounded-xl border border-gray-200 bg-white p-6 shadow-sm"
        >
          <Input
            id="slug"
            label="Workspace"
            type="text"
            placeholder="minha-empresa"
            value={slug}
            onChange={(e) => setSlug(e.target.value)}
            required
            autoComplete="organization"
            autoFocus
          />
          <Input
            id="email"
            label="Email"
            type="email"
            placeholder="voce@empresa.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            autoComplete="email"
          />
          <Input
            id="password"
            label="Senha"
            type="password"
            placeholder="••••••••"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            autoComplete="current-password"
          />

          {error && (
            <p className="text-sm text-red-600" role="alert">
              {error}
            </p>
          )}

          <Button type="submit" isLoading={isLoading} className="mt-2 w-full">
            Entrar
          </Button>
        </form>
      </div>
    </main>
  );
}
