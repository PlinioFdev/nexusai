// Hook para gerenciar documentos — upload, listagem, delete e polling de status.
// Polling é necessário porque o processamento é assíncrono (Celery).

import { useState, useEffect, useCallback } from "react";
import { api, ApiError } from "@/lib/api";
import type { DocumentResponse, DocumentListResponse } from "@/lib/types";

const POLL_INTERVAL_MS = 3000;

// Retorna true se algum documento ainda está sendo processado
function hasPendingDocuments(docs: DocumentResponse[]): boolean {
  return docs.some((d) => d.status === "PENDING" || d.status === "PROCESSING");
}

export interface UseDocumentsReturn {
  documents: DocumentResponse[];
  isLoading: boolean;
  isUploading: boolean;
  error: string | null;
  upload: (file: File) => Promise<void>;
  remove: (id: string) => Promise<void>;
  refresh: () => Promise<void>;
}

export function useDocuments(): UseDocumentsReturn {
  const [documents, setDocuments] = useState<DocumentResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchDocuments = useCallback(async () => {
    try {
      const data = await api.get<DocumentListResponse>("/api/v1/documents");
      setDocuments(data.items);
      setError(null);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      }
    }
  }, []);

  const refresh = useCallback(async () => {
    await fetchDocuments();
  }, [fetchDocuments]);

  // Carregamento inicial
  useEffect(() => {
    setIsLoading(true);
    fetchDocuments().finally(() => setIsLoading(false));
  }, [fetchDocuments]);

  // Polling enquanto houver documentos pendentes
  useEffect(() => {
    if (!hasPendingDocuments(documents)) return;

    const interval = setInterval(() => {
      fetchDocuments();
    }, POLL_INTERVAL_MS);

    return () => clearInterval(interval);
  }, [documents, fetchDocuments]);

  const upload = useCallback(async (file: File) => {
    setIsUploading(true);
    setError(null);
    try {
      const formData = new FormData();
      formData.append("file", file);
      await api.postForm<DocumentResponse>("/api/v1/documents/upload", formData);
      await fetchDocuments();
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      }
    } finally {
      setIsUploading(false);
    }
  }, [fetchDocuments]);

  const remove = useCallback(async (id: string) => {
    setError(null);
    try {
      await api.delete<null>(`/api/v1/documents/${id}`);
      setDocuments((prev) => prev.filter((d) => d.id !== id));
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      }
    }
  }, []);

  return { documents, isLoading, isUploading, error, upload, remove, refresh };
}
