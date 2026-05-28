import type { DocumentStatus } from "@/lib/types";

type Variant = "success" | "warning" | "error" | "info" | "neutral";

interface BadgeProps {
  children: React.ReactNode;
  variant?: Variant;
}

const variantClasses: Record<Variant, string> = {
  success: "bg-green-100 text-green-800",
  warning: "bg-yellow-100 text-yellow-800",
  error: "bg-red-100 text-red-800",
  info: "bg-blue-100 text-blue-800",
  neutral: "bg-gray-100 text-gray-800",
};

export function Badge({ children, variant = "neutral" }: BadgeProps) {
  return (
    <span
      className={[
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium",
        variantClasses[variant],
      ].join(" ")}
    >
      {children}
    </span>
  );
}

// Helper para mapear DocumentStatus → variant do Badge
export function statusVariant(status: DocumentStatus): Variant {
  const map: Record<DocumentStatus, Variant> = {
    PENDING: "neutral",
    PROCESSING: "warning",
    READY: "success",
    FAILED: "error",
  };
  return map[status];
}

// Label em português para exibição
export function statusLabel(status: DocumentStatus): string {
  const map: Record<DocumentStatus, string> = {
    PENDING: "Pendente",
    PROCESSING: "Processando",
    READY: "Pronto",
    FAILED: "Falhou",
  };
  return map[status];
}
