import { MessageSquare, Plus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/Button";
import type { ChatSessionResponse } from "@/lib/types";

interface SessionListProps {
  sessions: ChatSessionResponse[];
  activeSessionId: string | null;
  onSelect: (id: string) => void;
  onCreate: () => Promise<void>;
  onRemove: (id: string) => Promise<void>;
  isLoading: boolean;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
  });
}

export function SessionList({
  sessions,
  activeSessionId,
  onSelect,
  onCreate,
  onRemove,
  isLoading,
}: SessionListProps) {
  return (
    <aside className="flex h-full w-64 shrink-0 flex-col border-r border-gray-200 bg-white">
      <div className="flex items-center justify-between border-b border-gray-200 p-4">
        <h2 className="text-sm font-semibold text-gray-700">Conversas</h2>
        <Button
          variant="ghost"
          size="sm"
          onClick={onCreate}
          aria-label="Nova conversa"
        >
          <Plus className="h-4 w-4" />
        </Button>
      </div>

      <nav className="flex-1 overflow-y-auto p-2">
        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <span className="text-xs text-gray-400">Carregando...</span>
          </div>
        ) : sessions.length === 0 ? (
          <div className="flex flex-col items-center justify-center gap-2 py-8 text-gray-400">
            <MessageSquare className="h-8 w-8" />
            <p className="text-xs">Nenhuma conversa ainda.</p>
          </div>
        ) : (
          <ul className="flex flex-col gap-1">
            {sessions.map((session) => (
              <li key={session.id} className="group flex items-center gap-1">
                <button
                  onClick={() => onSelect(session.id)}
                  className={[
                    "flex flex-1 items-center rounded-md px-3 py-2 text-left text-sm transition-colors min-w-0",
                    activeSessionId === session.id
                      ? "bg-indigo-50 text-indigo-700 font-medium"
                      : "text-gray-700 hover:bg-gray-100",
                  ].join(" ")}
                >
                  <span className="truncate">
                    {session.title ?? `Conversa ${formatDate(session.created_at)}`}
                  </span>
                </button>
                <button
                  onClick={() => onRemove(session.id)}
                  aria-label="Remover conversa"
                  className="shrink-0 rounded-md p-1 opacity-0 group-hover:opacity-100 transition-opacity hover:bg-gray-100"
                >
                  <Trash2 className="h-3.5 w-3.5 text-gray-400 hover:text-red-500" />
                </button>
              </li>
            ))}
          </ul>
        )}
      </nav>
    </aside>
  );
}
