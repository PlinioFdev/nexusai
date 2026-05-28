import { api, ApiError } from "@/lib/api";
import * as auth from "@/lib/auth";

// Mock do fetch global
const mockFetch = jest.fn();
global.fetch = mockFetch;

// Mock do auth para controlar token
jest.mock("@/lib/auth", () => ({
  getAccessToken: jest.fn(),
  clearTokens: jest.fn(),
}));

const mockGetAccessToken = auth.getAccessToken as jest.MockedFunction<() => string | null>;
const mockClearTokens = auth.clearTokens as jest.MockedFunction<() => void>;

function mockResponse(status: number, body: unknown) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: jest.fn().mockResolvedValue(body),
  };
}

beforeEach(() => {
  jest.clearAllMocks();
  mockGetAccessToken.mockReturnValue(null);
  // Evita redirect no jsdom
  delete (window as unknown as Record<string, unknown>).location;
  (window as unknown as Record<string, unknown>).location = { href: "" };
});

describe("api.get", () => {
  it("faz GET e retorna JSON em caso de sucesso", async () => {
    mockFetch.mockResolvedValueOnce(mockResponse(200, { id: "1" }));

    const result = await api.get<{ id: string }>("/api/v1/test");

    expect(result).toEqual({ id: "1" });
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/test"),
      expect.objectContaining({ method: "GET" })
    );
  });

  it("injeta Authorization header quando há token", async () => {
    mockGetAccessToken.mockReturnValue("my-token");
    mockFetch.mockResolvedValueOnce(mockResponse(200, {}));

    await api.get("/api/v1/test");

    expect(mockFetch).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: "Bearer my-token",
        }),
      })
    );
  });

  it("não injeta Authorization header sem token", async () => {
    mockGetAccessToken.mockReturnValue(null);
    mockFetch.mockResolvedValueOnce(mockResponse(200, {}));

    await api.get("/api/v1/test");

    const callHeaders = mockFetch.mock.calls[0][1].headers;
    expect(callHeaders).not.toHaveProperty("Authorization");
  });
});

describe("api.post", () => {
  it("faz POST com body JSON", async () => {
    mockFetch.mockResolvedValueOnce(mockResponse(200, { ok: true }));

    await api.post("/api/v1/test", { name: "acme" });

    expect(mockFetch).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ name: "acme" }),
        headers: expect.objectContaining({
          "Content-Type": "application/json",
        }),
      })
    );
  });
});

describe("tratamento de erros", () => {
  it("lança ApiError com status e mensagem do backend", async () => {
    mockFetch.mockResolvedValueOnce(
      mockResponse(422, { detail: "Validação falhou" })
    );

    await expect(api.get("/api/v1/test")).rejects.toMatchObject({
      status: 422,
      message: "Validação falhou",
    });
  });

  it("lança ApiError com mensagem padrão quando body não tem detail", async () => {
    mockFetch.mockResolvedValueOnce(mockResponse(500, {}));

    await expect(api.get("/api/v1/test")).rejects.toMatchObject({
      status: 500,
      message: "Erro 500",
    });
  });

  it("em 401 chama clearTokens e redireciona", async () => {
    mockFetch.mockResolvedValueOnce(mockResponse(401, { detail: "Não autorizado" }));

    await expect(api.get("/api/v1/test")).rejects.toMatchObject({
      status: 401,
    });

    expect(mockClearTokens).toHaveBeenCalled();
  });

  it("ApiError é instância de Error", async () => {
    mockFetch.mockResolvedValueOnce(mockResponse(404, { detail: "Não encontrado" }));

    await expect(api.get("/api/v1/test")).rejects.toBeInstanceOf(ApiError);
  });
});

describe("api.delete", () => {
  it("retorna null em resposta 204", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 204,
      json: jest.fn(),
    });

    const result = await api.delete("/api/v1/test/1");
    expect(result).toBeNull();
  });
});
