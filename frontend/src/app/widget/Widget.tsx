// Widget embeddable do NexusAI.
// Montado via embed.ts em sites externos — não depende do contexto do dashboard.
// NÃO usar "use client" — este componente é compilado fora do pipeline Next.js.

import { useState, useRef, useEffect } from "react";
import { MessageSquare, X, Send, Bot, User } from "lucide-react";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
}

interface WidgetProps {
  apiKey: string;
  baseUrl: string;
}

async function sendWidgetMessage(
  baseUrl: string,
  apiKey: string,
  message: string,
  sessionId: string | null
): Promise<{ session_id: string; answer: string }> {
  const res = await fetch(`${baseUrl}/api/v1/widget/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ api_key: apiKey, message, session_id: sessionId }),
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `Erro ${res.status}`);
  }

  return res.json();
}

export function Widget({ apiKey, baseUrl }: WidgetProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isSending]);

  async function handleSend() {
    const trimmed = input.trim();
    if (!trimmed || isSending) return;

    setInput("");
    setError(null);

    const optimisticId = `opt-${Date.now()}`;
    setMessages((prev) => [
      ...prev,
      { id: optimisticId, role: "user", content: trimmed },
    ]);
    setIsSending(true);

    try {
      const data = await sendWidgetMessage(baseUrl, apiKey, trimmed, sessionId);
      setSessionId(data.session_id);
      setMessages((prev) => [
        ...prev.filter((m) => m.id !== optimisticId),
        { id: `u-${Date.now()}`, role: "user", content: trimmed },
        { id: `a-${Date.now()}`, role: "assistant", content: data.answer },
      ]);
    } catch (err) {
      setMessages((prev) => prev.filter((m) => m.id !== optimisticId));
      setError(err instanceof Error ? err.message : "Erro desconhecido");
    } finally {
      setIsSending(false);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col items-end gap-3">
      {isOpen && (
        <div className="flex h-[480px] w-80 flex-col rounded-xl border border-gray-200 bg-white shadow-xl">
          <div className="flex items-center justify-between rounded-t-xl bg-indigo-600 px-4 py-3">
            <div className="flex items-center gap-2">
              <Bot className="h-4 w-4 text-white" />
              <span className="text-sm font-semibold text-white">NexusAI</span>
            </div>
            <button
              onClick={() => setIsOpen(false)}
              aria-label="Fechar chat"
              className="text-indigo-200 hover:text-white transition-colors"
            >
              <X className="h-4 w-4" />
            </button>
          </div>

          <div className="flex flex-1 flex-col gap-3 overflow-y-auto p-3">
            {messages.length === 0 && !isSending && (
              <div className="flex flex-1 items-center justify-center">
                <p className="text-center text-xs text-gray-400">
                  Olá! Faça uma pergunta sobre nossos documentos.
                </p>
              </div>
            )}

            {messages.map((msg) => (
              <div
                key={msg.id}
                className={[
                  "flex gap-2",
                  msg.role === "user" ? "flex-row-reverse" : "flex-row",
                ].join(" ")}
              >
                <div
                  className={[
                    "flex h-6 w-6 shrink-0 items-center justify-center rounded-full",
                    msg.role === "user" ? "bg-indigo-600" : "bg-gray-200",
                  ].join(" ")}
                >
                  {msg.role === "user" ? (
                    <User className="h-3 w-3 text-white" />
                  ) : (
                    <Bot className="h-3 w-3 text-gray-600" />
                  )}
                </div>
                <div
                  className={[
                    "max-w-[80%] rounded-lg px-3 py-2 text-xs",
                    msg.role === "user"
                      ? "bg-indigo-600 text-white"
                      : "bg-gray-100 text-gray-900",
                  ].join(" ")}
                >
                  {msg.content}
                </div>
              </div>
            ))}

            {isSending && (
              <div className="flex gap-2">
                <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-gray-200">
                  <Bot className="h-3 w-3 text-gray-600" />
                </div>
                <div className="rounded-lg bg-gray-100 px-3 py-2">
                  <span className="flex gap-1">
                    <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-gray-400 [animation-delay:0ms]" />
                    <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-gray-400 [animation-delay:150ms]" />
                    <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-gray-400 [animation-delay:300ms]" />
                  </span>
                </div>
              </div>
            )}

            {error && (
              <p className="text-center text-xs text-red-500" role="alert">
                {error}
              </p>
            )}

            <div ref={bottomRef} />
          </div>

          <div className="border-t border-gray-200 p-3">
            <div className="flex gap-2 items-end">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                disabled={isSending}
                placeholder="Digite sua pergunta..."
                rows={1}
                className={[
                  "flex-1 resize-none rounded-md border border-gray-300 px-2 py-1.5 text-xs",
                  "placeholder:text-gray-400 focus:outline-none focus:ring-1 focus:ring-indigo-500",
                  "disabled:cursor-not-allowed disabled:bg-gray-50 max-h-20 overflow-y-auto",
                ].join(" ")}
              />
              <button
                onClick={handleSend}
                disabled={!input.trim() || isSending}
                aria-label="Enviar mensagem"
                className={[
                  "flex h-7 w-7 shrink-0 items-center justify-center rounded-md transition-colors",
                  input.trim() && !isSending
                    ? "bg-indigo-600 text-white hover:bg-indigo-700"
                    : "bg-gray-100 text-gray-400 cursor-not-allowed",
                ].join(" ")}
              >
                <Send className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>
        </div>
      )}

      <button
        onClick={() => setIsOpen((prev) => !prev)}
        aria-label={isOpen ? "Fechar chat" : "Abrir chat"}
        className="flex h-12 w-12 items-center justify-center rounded-full bg-indigo-600 shadow-lg hover:bg-indigo-700 transition-colors"
      >
        {isOpen ? (
          <X className="h-5 w-5 text-white" />
        ) : (
          <MessageSquare className="h-5 w-5 text-white" />
        )}
      </button>
    </div>
  );
}
