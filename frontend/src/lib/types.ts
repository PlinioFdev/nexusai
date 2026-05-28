// Types espelhando os schemas Pydantic do backend.
// Atualizar sempre que os schemas do backend mudarem.

// ── Auth ─────────────────────────────────────────────────────────────────────

export interface LoginRequest {
  email: string;
  password: string;
  slug: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  // refresh_token vai em httpOnly cookie — não exposto no body
}

export interface UserResponse {
  id: string;
  email: string;
  role: "OWNER" | "ADMIN" | "MEMBER";
  tenant_id: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

// ── Documents ────────────────────────────────────────────────────────────────

export type DocumentStatus = "PENDING" | "PROCESSING" | "READY" | "FAILED";

export interface DocumentResponse {
  id: string;
  tenant_id: string;
  filename: string;
  file_size: number;
  status: DocumentStatus;
  chunk_count: number | null;
  created_at: string;
  updated_at: string;
}

export interface DocumentListResponse {
  items: DocumentResponse[];
  total: number;
}

// ── Chat ─────────────────────────────────────────────────────────────────────

export interface ChatSessionResponse {
  id: string;
  tenant_id: string;
  user_id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface ChatSessionListResponse {
  items: ChatSessionResponse[];
  total: number;
}

export interface MessageResponse {
  id: string;
  session_id: string;
  role: "user" | "assistant";
  content: string;
  // source_chunks é JSON serializado no banco — string ou null, não array
  source_chunks: string | null;
  created_at: string;
}

export interface SendMessageRequest {
  content: string;
}

export interface SendMessageResponse {
  user_message: MessageResponse;
  assistant_message: MessageResponse;
}

export interface MessageListResponse {
  items: MessageResponse[];
  total: number;
}

// ── Widget ───────────────────────────────────────────────────────────────────

export interface WidgetConfig {
  apiKey: string;
  baseUrl?: string;
}
