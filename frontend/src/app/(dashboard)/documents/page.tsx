"use client";

import { useDocuments } from "@/hooks/useDocuments";
import { UploadZone } from "@/components/documents/UploadZone";
import { DocumentList } from "@/components/documents/DocumentList";

export default function DocumentsPage() {
  const { documents, isLoading, isUploading, error, upload, remove } =
    useDocuments();

  return (
    <div className="mx-auto w-full max-w-3xl px-6 py-8">
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-gray-900">Documentos</h1>
        <p className="mt-1 text-sm text-gray-500">
          Faça upload de PDFs ou TXTs para usar no chat RAG.
        </p>
      </div>

      <div className="flex flex-col gap-6">
        <section>
          <UploadZone onUpload={upload} isUploading={isUploading} />
        </section>

        {error && (
          <p className="text-sm text-red-600" role="alert">
            {error}
          </p>
        )}

        <section>
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <span className="text-sm text-gray-400">
                Carregando documentos...
              </span>
            </div>
          ) : (
            <DocumentList documents={documents} onRemove={remove} />
          )}
        </section>
      </div>
    </div>
  );
}
