export interface DocumentSummary {
  document_name: string;
  total_pages: number;
  total_rows: number;
  has_tables: boolean;
  report_date?: string | null;
  created_at?: string | null;
}

export interface DocumentExtraction {
  id: number;
  document_name: string;
  page_number?: number | null;
  raw_text?: string | null;
  tables: unknown;
  metadata: Record<string, unknown>;
  created_at?: string | null;
}

export interface ExtractionResponse {
  items: DocumentExtraction[];
  total: number;
  limit: number;
  offset: number;
}

export interface IngestionUploadResponse {
  job_id: string;
  status: string;
  filename: string;
  s3_key: string;
  size_bytes: number;
}

export interface IngestionJobResponse {
  id: string;
  s3_key: string;
  original_filename: string;
  status: string;
  error_message?: string | null;
  created_at?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
}

export interface SessionResponse {
  session_id: string;
  name: string;
}

export interface Message {
  role: "system" | "user" | "assistant" | "tool";
  content: string;
  title?: string | null;
  metadata?: Record<string, unknown>;
}

export interface ChatResponse {
  messages: Message[];
}

export interface PrecedentSuggestion {
  title: string;
  rationale: string;
}

export interface OffenceOption {
  value: string;
  title: string;
  subtitle: string;
  precedentSeed: PrecedentSuggestion[];
}

export interface AiInsightPayload {
  strength_summary?: string;
  success_probability?: number;
  precedents?: PrecedentSuggestion[];
  recommendation?: string;
  notes?: string;
}

export interface DraftArgument {
  title: string;
  body: string;
}

export interface DraftModel {
  referenceNumber: string;
  letterDate: string;
  openingParagraph: string;
  contextParagraph: string;
  closingParagraph: string;
  arguments: DraftArgument[];
  internalReference: string;
  documentId: string;
}
