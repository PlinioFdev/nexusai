import { renderHook, act, waitFor } from "@testing-library/react";
import { useDocuments } from "@/hooks/useDocuments";
import { api, ApiError } from "@/lib/api";
import type { DocumentResponse } from "@/lib/types";

jest.mock("@/lib/api", () => ({
  api: {
    get: jest.fn(),
    postForm: jest.fn(),
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

const MOCK_DOC: DocumentResponse = {
  id: "doc-1",
  tenant_id: "tenant-1",
  filename: "relatorio.pdf",
  file_size: 1024,
  status: "READY",
  chunk_count: 10,
  created_at: "2024-01-01T00:00:00Z",
  updated_at: "2024-01-01T00:00:00Z",
};

const MOCK_PENDING_DOC: DocumentResponse = {
  ...MOCK_DOC,
  id: "doc-2",
  status: "PENDING",
  chunk_count: null,
};

beforeEach(() => {
  jest.clearAllMocks();
  jest.useFakeTimers();
});

afterEach(() => {
  jest.useRealTimers();
});

describe("useDocuments — carregamento inicial", () => {
  it("carrega documentos na montagem", async () => {
    mockApi.get.mockResolvedValueOnce({ items: [MOCK_DOC], total: 1 });

    const { result } = renderHook(() => useDocuments());

    expect(result.current.isLoading).toBe(true);

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.documents).toEqual([MOCK_DOC]);
    expect(result.current.error).toBeNull();
  });

  it("define error quando fetch falha", async () => {
    mockApi.get.mockRejectedValueOnce(new ApiError(500, "Erro interno"));

    const { result } = renderHook(() => useDocuments());

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.error).toBe("Erro interno");
    expect(result.current.documents).toEqual([]);
  });
});

describe("useDocuments — upload", () => {
  it("faz upload e recarrega a lista", async () => {
    mockApi.get.mockResolvedValue({ items: [MOCK_DOC], total: 1 });
    mockApi.postForm.mockResolvedValueOnce(MOCK_DOC);

    const { result } = renderHook(() => useDocuments());
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    const file = new File(["content"], "relatorio.pdf", { type: "application/pdf" });

    await act(async () => {
      await result.current.upload(file);
    });

    expect(mockApi.postForm).toHaveBeenCalledWith(
      "/api/v1/documents/upload",
      expect.any(FormData)
    );
    expect(mockApi.get).toHaveBeenCalledTimes(2);
  });

  it("define error quando upload falha", async () => {
    mockApi.get.mockResolvedValue({ items: [], total: 0 });
    mockApi.postForm.mockRejectedValueOnce(new ApiError(422, "Extensão inválida"));

    const { result } = renderHook(() => useDocuments());
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    const file = new File(["content"], "arquivo.exe", { type: "application/octet-stream" });

    await act(async () => {
      await result.current.upload(file);
    });

    expect(result.current.error).toBe("Extensão inválida");
  });
});

describe("useDocuments — remove", () => {
  it("remove documento da lista otimisticamente", async () => {
    mockApi.get.mockResolvedValueOnce({ items: [MOCK_DOC], total: 1 });
    mockApi.delete.mockResolvedValueOnce(null);

    const { result } = renderHook(() => useDocuments());
    await waitFor(() => expect(result.current.documents).toHaveLength(1));

    await act(async () => {
      await result.current.remove("doc-1");
    });

    expect(result.current.documents).toHaveLength(0);
  });
});

describe("useDocuments — polling", () => {
  it("inicia polling quando há documentos pendentes", async () => {
    mockApi.get
      .mockResolvedValueOnce({ items: [MOCK_PENDING_DOC], total: 1 })
      .mockResolvedValueOnce({ items: [{ ...MOCK_PENDING_DOC, status: "READY" }], total: 1 });

    const { result } = renderHook(() => useDocuments());
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.documents[0].status).toBe("PENDING");

    await act(async () => {
      jest.advanceTimersByTime(3000);
    });

    await waitFor(() =>
      expect(result.current.documents[0].status).toBe("READY")
    );
  });
});
