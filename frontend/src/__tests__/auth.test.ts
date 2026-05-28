import {
  saveTokens,
  clearTokens,
  getAccessToken,
  getRefreshToken,
  getTenantSlug,
  getStoredUser,
  isAuthenticated,
  isTokenExpired,
} from "@/lib/auth";
import type { UserResponse } from "@/lib/types";

const MOCK_USER: UserResponse = {
  id: "user-1",
  email: "owner@acme.com",
  role: "OWNER",
  tenant_id: "tenant-1",
  is_active: true,
  created_at: "2024-01-01T00:00:00Z",
  updated_at: "2024-01-01T00:00:00Z",
};

// JWT com exp no futuro (ano 2099)
const VALID_TOKEN =
  "eyJhbGciOiJIUzI1NiJ9." +
  btoa(JSON.stringify({ sub: "user-1", exp: 4102444800 })).replace(/=/g, "") +
  ".signature";

// JWT com exp no passado
const EXPIRED_TOKEN =
  "eyJhbGciOiJIUzI1NiJ9." +
  btoa(JSON.stringify({ sub: "user-1", exp: 1 })).replace(/=/g, "") +
  ".signature";

beforeEach(() => {
  localStorage.clear();
});

describe("saveTokens / clearTokens", () => {
  it("salva access token, slug e user", () => {
    saveTokens("access-123", "acme", MOCK_USER);

    expect(getAccessToken()).toBe("access-123");
    expect(getTenantSlug()).toBe("acme");
    expect(getStoredUser()).toEqual(MOCK_USER);
  });

  it("salva refresh token quando fornecido", () => {
    saveTokens("access-123", "acme", MOCK_USER, "refresh-456");

    expect(getRefreshToken()).toBe("refresh-456");
  });

  it("não persiste refresh token quando omitido", () => {
    saveTokens("access-123", "acme", MOCK_USER);

    expect(getRefreshToken()).toBeNull();
  });

  it("clearTokens remove todos os valores", () => {
    saveTokens("access-123", "acme", MOCK_USER, "refresh-456");
    clearTokens();

    expect(getAccessToken()).toBeNull();
    expect(getRefreshToken()).toBeNull();
    expect(getTenantSlug()).toBeNull();
    expect(getStoredUser()).toBeNull();
  });
});

describe("isTokenExpired", () => {
  it("retorna false para token válido (exp no futuro)", () => {
    expect(isTokenExpired(VALID_TOKEN)).toBe(false);
  });

  it("retorna true para token expirado (exp no passado)", () => {
    expect(isTokenExpired(EXPIRED_TOKEN)).toBe(true);
  });

  it("retorna true para string inválida", () => {
    expect(isTokenExpired("nao-e-um-jwt")).toBe(true);
  });

  it("retorna true para token sem exp", () => {
    const noExp =
      "eyJhbGciOiJIUzI1NiJ9." +
      btoa(JSON.stringify({ sub: "user-1" })).replace(/=/g, "") +
      ".signature";
    expect(isTokenExpired(noExp)).toBe(true);
  });
});

describe("isAuthenticated", () => {
  it("retorna false sem token salvo", () => {
    expect(isAuthenticated()).toBe(false);
  });

  it("retorna false com token expirado", () => {
    saveTokens(EXPIRED_TOKEN, "acme", MOCK_USER);
    expect(isAuthenticated()).toBe(false);
  });

  it("retorna true com token válido", () => {
    saveTokens(VALID_TOKEN, "acme", MOCK_USER);
    expect(isAuthenticated()).toBe(true);
  });
});
