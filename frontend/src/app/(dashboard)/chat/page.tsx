"use client";

import { useState, useCallback } from "react";
import { useSessions, useMessages } from "@/hooks/useChat";
import { SessionList } from "@/components/chat/SessionList";
import { MessageThread } from "@/components/chat/MessageThread";
import { MessageInput } from "@/components/chat/MessageInput";

export default function ChatPage() {
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);

  const { sessions, isLoadingSessions, sessionsError, createSession, removeSession } =
    useSessions();

  const { messages, isLoadingMessages, isSending, messagesError, sendMessage } =
    useMessages(activeSessionId);

  const handleCreateSession = useCallback(async () => {
    const session = await createSession();
    if (session) {
      setActiveSessionId(session.id);
    }
  }, [createSession]);

  const handleRemoveSession = useCallback(
    async (id: string) => {
      await removeSession(id);
      if (activeSessionId === id) {
        setActiveSessionId(null);
      }
    },
    [removeSession, activeSessionId]
  );

  return (
    <div className="flex flex-1 overflow-hidden">
      <SessionList
        sessions={sessions}
        activeSessionId={activeSessionId}
        onSelect={setActiveSessionId}
        onCreate={handleCreateSession}
        onRemove={handleRemoveSession}
        isLoading={isLoadingSessions}
      />

      <div className="flex flex-1 flex-col overflow-hidden">
        {sessionsError && (
          <p className="bg-red-50 px-4 py-2 text-sm text-red-600" role="alert">
            {sessionsError}
          </p>
        )}

        {!activeSessionId ? (
          <div className="flex flex-1 flex-col items-center justify-center gap-3 text-gray-400">
            <p className="text-sm">Selecione ou crie uma conversa para começar.</p>
          </div>
        ) : (
          <>
            <MessageThread
              messages={messages}
              isLoading={isLoadingMessages}
              isSending={isSending}
            />

            {messagesError && (
              <p className="bg-red-50 px-4 py-2 text-sm text-red-600" role="alert">
                {messagesError}
              </p>
            )}

            <MessageInput
              onSend={sendMessage}
              isSending={isSending}
              disabled={isLoadingMessages}
            />
          </>
        )}
      </div>
    </div>
  );
}
