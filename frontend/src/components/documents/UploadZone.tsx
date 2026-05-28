// Zona de upload com drag-and-drop.
// Aceita apenas PDF e TXT, máximo 20MB (espelhando validação do backend).

import { useRef, useState, type DragEvent, type ChangeEvent } from "react";
import { Upload } from "lucide-react";
import { Button } from "@/components/ui/Button";

const ACCEPTED_EXTENSIONS = [".pdf", ".txt"];
const MAX_SIZE_BYTES = 20 * 1024 * 1024; // 20MB

interface UploadZoneProps {
  onUpload: (file: File) => Promise<void>;
  isUploading: boolean;
}

function validateFile(file: File): string | null {
  const ext = "." + file.name.split(".").pop()?.toLowerCase();
  if (!ACCEPTED_EXTENSIONS.includes(ext)) {
    return "Apenas arquivos PDF e TXT são aceitos.";
  }
  if (file.size > MAX_SIZE_BYTES) {
    return "O arquivo deve ter no máximo 20MB.";
  }
  return null;
}

export function UploadZone({ onUpload, isUploading }: UploadZoneProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);

  function handleFile(file: File) {
    const error = validateFile(file);
    if (error) {
      setValidationError(error);
      return;
    }
    setValidationError(null);
    onUpload(file);
  }

  function handleDragOver(e: DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setIsDragging(true);
  }

  function handleDragLeave() {
    setIsDragging(false);
  }

  function handleDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  }

  function handleChange(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
    // Reset input para permitir re-upload do mesmo arquivo
    e.target.value = "";
  }

  return (
    <div className="flex flex-col gap-2">
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
        className={[
          "flex cursor-pointer flex-col items-center justify-center gap-3",
          "rounded-lg border-2 border-dashed p-8 transition-colors",
          isDragging
            ? "border-indigo-500 bg-indigo-50"
            : "border-gray-300 hover:border-indigo-400 hover:bg-gray-50",
          isUploading ? "pointer-events-none opacity-60" : "",
        ].join(" ")}
      >
        <Upload className="h-8 w-8 text-gray-400" />
        <div className="text-center">
          <p className="text-sm font-medium text-gray-700">
            Arraste um arquivo ou clique para selecionar
          </p>
          <p className="text-xs text-gray-500 mt-1">PDF ou TXT — máximo 20MB</p>
        </div>
        <Button variant="secondary" size="sm" isLoading={isUploading} type="button">
          Selecionar arquivo
        </Button>
      </div>

      <input
        ref={inputRef}
        type="file"
        accept=".pdf,.txt"
        className="hidden"
        onChange={handleChange}
        aria-label="Selecionar arquivo para upload"
      />

      {validationError && (
        <p className="text-xs text-red-600" role="alert">
          {validationError}
        </p>
      )}
    </div>
  );
}
