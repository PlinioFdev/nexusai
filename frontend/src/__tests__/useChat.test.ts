import { renderHook, act, waitFor } from "@testing-library/react";
import { useSessions, useMessages } from "@/hooks/useChat";
import { api, ApiError } from "@/lib/api";
import type { ChatSessionResponse, MessageResponse } from "@/lib/types";

jest.mock("@/lib/api", () => ({
  api: {
    get: jest.fn(),
    post: jest.fn(),
    delete: jest.fn(),
  },
  ApiError: class ApiError extends Error {
    constructor(
      public status: number,
      message: string
    ) {
      super(message);
    }
  },
}));

const mockApi = api as jest.Mocked<typeof api>;

const MOCK_SESSION: ChatSessionResponse = {
  id: "session-1",
  tenant_id: "tenant-1",
  title: "Teste",
  created_at: "2024-01-01T00:00:00Z",
  updated_at: "2024-01-01T00:00:00Z",
};

const MOCK_USER_MSG: MessageResponse = {
  id: "msg-1",
  session_id: "session-1",
  role: "user",
  content: "Qual o prazo?",
  source_chunks: null,
  created_at: "2024-01-01T00:00:00Z",
};

const MOCK_ASSISTANT_MSG: MessageResponse = {
  id: "msg-2",
  session_id: "session-1",
  role: "assistant",
  content: "O prazo é 30 dias.",
  source_chunks: ["chunk-1"],
  created_at: "2024-01-01T00:00:01Z",
};

beforeEach(() => {
  jest.clearAllMocks();
});

// ── useSessions ───────────────────────────────────────────────────────────────

describe("useSessions — carregamento", () => {
  it("carrega sessões na montagem", async () => {
    mockApi.get.mockResolvedValueOnce({ items: [MOCK_SESSION], total: 1 });

    const { result } = renderHook(() => useSessions());

    await waitFor(() => expect(result.current.isLoadingSessions).toBe(false));

    expect(result.current.sessions).toEqual([MOCK_SESSION]);
    expect(result.current.sessionsError).toBeNull();
  });

  it("define error quando fetch falha", async () => {
    mockApi.get.mockRejectedValueOnce(new ApiError(500, "Erro interno"));

    const { result } = renderHook(() => useSessions());

    await waitFor(() => expect(result.current.isLoadingSessions).toBe(false));

    expect(result.current.sessionsError).toBe("Erro interno");
  });
});

describe("useSessions — createSession", () => {
  it("cria sessão e adiciona ao início da lista", async () => {
    mockApi.get.mockResolvedValueOnce({ items: [], total: 0 });
    mockApi.post.mockResolvedValueOnce(MOCK_SESSION);

    const { result } = renderHook(() => useSessions());
    await waitFor(() => expect(result.current.isLoadingSessions).toBe(false));

    let created: ChatSessionResponse | null = null;
    await act(async () => {
      created = await result.current.createSession("Teste");
    });

    expect(created).toEqual(MOCK_SESSION);
    expect(result.current.sessions[0]).toEqual(MOCK_SESSION);
  });

  it("retorna null quando criação falha", async () => {
    mockApi.get.mockResolvedValueOnce({ items: [], total: 0 });
    mockApi.post.mockRejectedValueOnce(new ApiError(422, "Inválido"));

    const { result } = renderHook(() => useSessions());
    await waitFor(() => expect(result.current.isLoadingSessions).toBe(false));

    let created: ChatSessionResponse | null = MOCK_SESSION;
    await act(async () => {
      created = await result.current.createSession();
    });

    expect(created).toBeNull();
    expect(result.current.sessionsError).toBe("Inválido");
  });
});

describe("useSessions — removeSession", () => {
  it("remove sessão da lista", async () => {
    mockApi.get.mockResolvedValueOnce({ items: [MOCK_SESSION], total: 1 });
    mockApi.delete.mockResolvedValueOnce(null);

    const { result } = renderHook(() => useSessions());
    await waitFor(() => expect(result.current.sessions).toHaveLength(1));

    await act(async () => {
      await result.current.removeSession("session-1");
    });

    expect(result.current.sessions).toHaveLength(0);
  });
});

// ── useMessages ───────────────────────────────────────────────────────────────

describe("useMessages — carregamento", () => {
  it("não faz fetch quando sessionId é null", () => {
    renderHook(() => useMessages(null));
    expect(mockApi.get).not.toHaveBeenCalled();
  });

  it("carrega mensagens quando sessionId é fornecido", async () => {
    mockApi.get.mockResolvedValueOnce({
      items: [MOCK_USER_MSG, MOCK_ASSISTANT_MSG],
      total: 2,
    });

    const { result } = renderHook(() => useMessages("session-1"));

    await waitFor(() => expect(result.current.isLoadingMessages).toBe(false));

    expect(result.current.messages).toHaveLength(2);
  });
});

describe("useMessages — sendMessage", () => {
  it("adiciona mensagem otimista e substitui pela real", async () => {
    mockApi.get.mockResolvedValueOnce({ items: [], total: 0 });
    mockApi.post.mockResolvedValueOnce({
      user_message: MOCK_USER_MSG,
      assistant_message: MOCK_ASSISTANT_MSG,
    });

    const { result } = renderHook(() => useMessages("session-1"));
    await waitFor(() => expect(result.current.isLoadingMessages).toBe(false));

    await act(async () => {
      await result.current.sendMessage("Qual o prazo?");
    });

    expect(result.current.messages).toHaveLength(2);
    expect(result.current.messages[0].role).toBe("user");
    expect(result.current.messages[1].role).toBe("assistant");
    expect(result.current.messages[1].content).toBe("O prazo é 30 dias.");
  });

  it("remove mensagem otimista quando envio falha", async () => {
    mockApi.get.mockResolvedValueOnce({ items: [], total: 0 });
    mockApi.post.mockRejectedValueOnce(new ApiError(500, "Erro interno"));

    const { result } = renderHook(() => useMessages("session-1"));
    await waitFor(() => expect(result.current.isLoadingMessages).toBe(false));

    await act(async () => {
      await result.current.sendMessage("Pergunta");
    });

    expect(result.current.messages).toHaveLength(0);
    expect(result.current.messagesError).toBe("Erro interno");
  });
});
