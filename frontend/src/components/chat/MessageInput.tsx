import { useState, type KeyboardEvent } from "react";
import { Send } from "lucide-react";
import { Button } from "@/components/ui/Button";

interface MessageInputProps {
  onSend: (content: string) => Promise<void>;
  isSending: boolean;
  disabled?: boolean;
}

export function MessageInput({ onSend, isSending, disabled }: MessageInputProps) {
  const [value, setValue] = useState("");

  async function handleSend() {
    const trimmed = value.trim();
    if (!trimmed || isSending) return;
    setValue("");
    await onSend(trimmed);
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    // Enter sem Shift envia — Shift+Enter quebra linha
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  return (
    <div className="border-t border-gray-200 bg-white p-4">
      <div className="flex gap-2 items-end">
        <textarea
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled || isSending}
          placeholder="Faça uma pergunta sobre seus documentos... (Enter para enviar)"
          rows={1}
          className={[
            "flex-1 resize-none rounded-md border border-gray-300 px-3 py-2 text-sm",
            "placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500",
            "disabled:cursor-not-allowed disabled:bg-gray-50 max-h-32 overflow-y-auto",
          ].join(" ")}
        />
        <Button
          onClick={handleSend}
          disabled={!value.trim() || disabled}
          isLoading={isSending}
          size="md"
          aria-label="Enviar mensagem"
        >
          <Send className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}
