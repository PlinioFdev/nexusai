import { useEffect, useRef } from "react";
import { Bot, User } from "lucide-react";
import type { MessageResponse } from "@/lib/types";

interface MessageThreadProps {
  messages: MessageResponse[];
  isLoading: boolean;
  isSending: boolean;
}

function parseSourceChunks(raw: string | null): string[] {
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function MessageThread({ messages, isLoading, isSending }: MessageThreadProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isSending]);

  if (isLoading) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <span className="text-sm text-gray-400">Carregando mensagens...</span>
      </div>
    );
  }

  if (messages.length === 0 && !isSending) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-2 text-gray-400">
        <Bot className="h-10 w-10" />
        <p className="text-sm">Faça uma pergunta sobre seus documentos.</p>
      </div>
    );
  }

  return (
    <div className="flex flex-1 flex-col gap-4 overflow-y-auto p-4">
      {messages.map((msg) => {
        const chunks = parseSourceChunks(msg.source_chunks);
        return (
          <div
            key={msg.id}
            className={[
              "flex gap-3",
              msg.role === "user" ? "flex-row-reverse" : "flex-row",
            ].join(" ")}
          >
            <div
              className={[
                "flex h-8 w-8 shrink-0 items-center justify-center rounded-full",
                msg.role === "user" ? "bg-indigo-600" : "bg-gray-200",
              ].join(" ")}
            >
              {msg.role === "user" ? (
                <User className="h-4 w-4 text-white" />
              ) : (
                <Bot className="h-4 w-4 text-gray-600" />
              )}
            </div>

            <div
              className={[
                "max-w-[75%] rounded-lg px-4 py-2.5 text-sm",
                msg.role === "user"
                  ? "bg-indigo-600 text-white"
                  : "bg-gray-100 text-gray-900",
              ].join(" ")}
            >
              <p className="whitespace-pre-wrap">{msg.content}</p>
              {chunks.length > 0 && (
                <p className="mt-1.5 text-xs opacity-60">
                  {chunks.length} fonte{chunks.length > 1 ? "s" : ""}
                </p>
              )}
            </div>
          </div>
        );
      })}

      {isSending && (
        <div className="flex gap-3">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gray-200">
            <Bot className="h-4 w-4 text-gray-600" />
          </div>
          <div className="rounded-lg bg-gray-100 px-4 py-2.5">
            <span className="flex gap-1">
              <span className="h-2 w-2 animate-bounce rounded-full bg-gray-400 [animation-delay:0ms]" />
              <span className="h-2 w-2 animate-bounce rounded-full bg-gray-400 [animation-delay:150ms]" />
              <span className="h-2 w-2 animate-bounce rounded-full bg-gray-400 [animation-delay:300ms]" />
            </span>
          </div>
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  );
}
