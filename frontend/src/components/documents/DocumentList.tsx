import { FileText, Trash2, RefreshCw } from "lucide-react";
import { Badge, statusVariant, statusLabel } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import type { DocumentResponse } from "@/lib/types";

interface DocumentListProps {
  documents: DocumentResponse[];
  onRemove: (id: string) => Promise<void>;
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}

export function DocumentList({ documents, onRemove }: DocumentListProps) {
  if (documents.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center gap-2 py-12 text-gray-400">
        <FileText className="h-10 w-10" />
        <p className="text-sm">Nenhum documento ainda.</p>
      </div>
    );
  }

  return (
    <ul className="divide-y divide-gray-100">
      {documents.map((doc) => (
        <li key={doc.id} className="flex items-center justify-between gap-4 py-3">
          <div className="flex items-center gap-3 min-w-0">
            <FileText className="h-5 w-5 shrink-0 text-gray-400" />
            <div className="min-w-0">
              <p className="truncate text-sm font-medium text-gray-900">
                {doc.filename}
              </p>
              <p className="text-xs text-gray-500">
                {formatBytes(doc.file_size)} · {formatDate(doc.created_at)}
                {doc.chunk_count != null && ` · ${doc.chunk_count} chunks`}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3 shrink-0">
            {(doc.status === "PENDING" || doc.status === "PROCESSING") && (
              <RefreshCw className="h-3.5 w-3.5 animate-spin text-yellow-500" />
            )}
            <Badge variant={statusVariant(doc.status)}>
              {statusLabel(doc.status)}
            </Badge>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onRemove(doc.id)}
              aria-label={`Remover ${doc.filename}`}
            >
              <Trash2 className="h-4 w-4 text-gray-400 hover:text-red-500" />
            </Button>
          </div>
        </li>
      ))}
    </ul>
  );
}
