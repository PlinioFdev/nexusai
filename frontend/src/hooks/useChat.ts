// Hook para gerenciar sessões de chat e envio de mensagens RAG.

import { useState, useEffect, useCallback } from "react";
import { api, ApiError } from "@/lib/api";
import type {
  ChatSessionResponse,
  ChatSessionListResponse,
  MessageResponse,
  MessageListResponse,
  SendMessageResponse,
} from "@/lib/types";

export interface UseChatsReturn {
  sessions: ChatSessionResponse[];
  isLoadingSessions: boolean;
  sessionsError: string | null;
  createSession: (title?: string) => Promise<ChatSessionResponse | null>;
  removeSession: (id: string) => Promise<void>;
}

export interface UseMessagesReturn {
  messages: MessageResponse[];
  isLoadingMessages: boolean;
  isSending: boolean;
  messagesError: string | null;
  sendMessage: (content: string) => Promise<void>;
}

// ── Sessões ───────────────────────────────────────────────────────────────────

export function useSessions(): UseChatsReturn {
  const [sessions, setSessions] = useState<ChatSessionResponse[]>([]);
  const [isLoadingSessions, setIsLoadingSessions] = useState(true);
  const [sessionsError, setSessionsError] = useState<string | null>(null);

  const fetchSessions = useCallback(async () => {
    try {
      const data = await api.get<ChatSessionListResponse>("/api/v1/chat/sessions");
      setSessions(data.items);
      setSessionsError(null);
    } catch (err) {
      if (err instanceof ApiError) {
        setSessionsError(err.message);
      }
    }
  }, []);

  useEffect(() => {
    setIsLoadingSessions(true);
    fetchSessions().finally(() => setIsLoadingSessions(false));
  }, [fetchSessions]);

  const createSession = useCallback(async (title?: string): Promise<ChatSessionResponse | null> => {
    try {
      // Omite title quando não fornecido — Pydantic usa o default "Nova conversa"
      // Enviar title: null causa 422 porque o schema espera str, não null
      const session = await api.post<ChatSessionResponse>(
        "/api/v1/chat/sessions",
        title ? { title } : {}
      );
      setSessions((prev) => [session, ...prev]);
      setSessionsError(null);
      return session;
    } catch (err) {
      if (err instanceof ApiError) {
        setSessionsError(err.message);
      }
      return null;
    }
  }, []);

  const removeSession = useCallback(async (id: string) => {
    try {
      await api.delete<null>(`/api/v1/chat/sessions/${id}`);
      setSessions((prev) => prev.filter((s) => s.id !== id));
      setSessionsError(null);
    } catch (err) {
      if (err instanceof ApiError) {
        setSessionsError(err.message);
      }
    }
  }, []);

  return { sessions, isLoadingSessions, sessionsError, createSession, removeSession };
}

// ── Mensagens ─────────────────────────────────────────────────────────────────

export function useMessages(sessionId: string | null): UseMessagesReturn {
  const [messages, setMessages] = useState<MessageResponse[]>([]);
  const [isLoadingMessages, setIsLoadingMessages] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [messagesError, setMessagesError] = useState<string | null>(null);

  useEffect(() => {
    if (!sessionId) {
      setMessages([]);
      return;
    }

    setIsLoadingMessages(true);
    api
      .get<MessageListResponse>(`/api/v1/chat/sessions/${sessionId}/messages`)
      .then((data) => {
        setMessages(data.items);
        setMessagesError(null);
      })
      .catch((err) => {
        if (err instanceof ApiError) {
          setMessagesError(err.message);
        }
      })
      .finally(() => setIsLoadingMessages(false));
  }, [sessionId]);

  const sendMessage = useCallback(
    async (content: string) => {
      if (!sessionId) return;

      setIsSending(true);
      setMessagesError(null);

      const optimisticUserMsg: MessageResponse = {
        id: `optimistic-${Date.now()}`,
        session_id: sessionId,
        role: "user",
        content,
        source_chunks: null,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, optimisticUserMsg]);

      try {
        const data = await api.post<SendMessageResponse>(
          `/api/v1/chat/sessions/${sessionId}/messages`,
          { content }
        );
        setMessages((prev) => [
          ...prev.filter((m) => m.id !== optimisticUserMsg.id),
          data.user_message,
          data.assistant_message,
        ]);
      } catch (err) {
        setMessages((prev) => prev.filter((m) => m.id !== optimisticUserMsg.id));
        if (err instanceof ApiError) {
          setMessagesError(err.message);
        }
      } finally {
        setIsSending(false);
      }
    },
    [sessionId]
  );

  return { messages, isLoadingMessages, isSending, messagesError, sendMessage };
}
