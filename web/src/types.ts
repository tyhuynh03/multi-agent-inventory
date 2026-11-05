export interface TablePayload {
  columns: string[]
  rows: unknown[][]
  /** null khi backend cắt dòng: fetchmany không biết tổng thật, chỉ biết còn nhiều hơn. */
  row_count: number | null
  returned_rows: number
  truncated: boolean
}

export interface ChartPayload {
  spec: { data: unknown[]; layout: Record<string, unknown> }
  viz_spec?: Record<string, unknown> | null
}

export interface IntentPayload {
  intent: string
  confidence: number
  reasoning: string
  duration_ms: number
}

export interface AnswerPayload {
  text: string | null
  message: string | null
  intent: string | null
  agent: string | null
  analytics_type: string | null
  success: boolean
}

export interface ErrorPayload {
  message: string
  type?: string
  intent?: string
  sql?: string
}

export interface TimingStep {
  step: string
  duration_ms: number
}

export interface SseFrame {
  name: string
  data: unknown
}

export interface TimelineEvent {
  name: string
  atMs: number
  label: string
}

export interface Turn {
  id: number
  question: string
  running: boolean
  events: TimelineEvent[]
  intent?: IntentPayload
  sql?: string
  table?: TablePayload
  chart?: ChartPayload
  schemaMarkdown?: string
  timings?: TimingStep[]
  answer?: AnswerPayload
  error?: ErrorPayload
  elapsedMs?: number
}

export interface HealthResponse {
  status: 'ok' | 'degraded'
  db: { ok: boolean; tables?: string[]; error?: string; elapsed_ms?: number }
  model: string
  limits: { max_rows: number; statement_timeout_ms: number }
  ai_pipeline: {
    groq_api_key_configured: boolean
    examples_path: string
    rag_top_k: number
  }
}

export interface SqlConsoleResponse extends TablePayload {
  sql: string
  elapsed_ms: number
}

export interface SchemaColumn {
  name: string
  type: string
  nullable: boolean
}

export interface SchemaTable {
  table: string
  columns: SchemaColumn[]
}
