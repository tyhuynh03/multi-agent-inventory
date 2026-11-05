import type {
  AnswerPayload,
  ChartPayload,
  ErrorPayload,
  IntentPayload,
  SseFrame,
  TablePayload,
  TimingStep,
  Turn,
} from './types'

const EVENT_LABELS: Record<string, string> = {
  start: 'Gửi câu hỏi',
  executing: 'Đang chạy truy vấn',
  sql: 'LLM sinh SQL',
  chart_planning: 'LLM chọn loại biểu đồ',
  analytics: 'Chạy analytics tồn kho',
  chart: 'Vẽ biểu đồ',
  schema: 'Đọc schema',
  timings: 'Tổng hợp thời gian từng bước',
  answer: 'Trả lời',
  error: 'Lỗi',
}

function labelFor(name: string, data: unknown): string {
  if (name === 'intent') {
    const intent = data as IntentPayload
    return `Intent: ${intent.intent} · ${Math.round(intent.confidence * 100)}%`
  }
  if (name === 'table') {
    const table = data as TablePayload
    return table.truncated
      ? `${table.returned_rows} dòng (đã cắt theo giới hạn)`
      : `${table.row_count ?? table.returned_rows} dòng kết quả`
  }
  if (name === 'done') {
    const { elapsed_ms } = data as { elapsed_ms?: number }
    return `Xong trong ${((elapsed_ms ?? 0) / 1000).toFixed(1)}s`
  }
  return EVENT_LABELS[name] ?? name
}

export function createTurn(id: number, question: string): Turn {
  return { id, question, running: true, events: [] }
}

export function reduceTurn(turn: Turn, frame: SseFrame, atMs: number): Turn {
  const { name, data } = frame
  const withEvent: Turn = {
    ...turn,
    events: [...turn.events, { name, atMs, label: labelFor(name, data) }],
  }

  switch (name) {
    case 'intent':
      return { ...withEvent, intent: data as IntentPayload }
    case 'sql':
      return { ...withEvent, sql: (data as { sql?: string }).sql }
    case 'table':
      return { ...withEvent, table: data as TablePayload }
    case 'chart':
      return { ...withEvent, chart: data as ChartPayload }
    case 'schema':
      return { ...withEvent, schemaMarkdown: (data as { markdown?: string }).markdown }
    case 'timings':
      return { ...withEvent, timings: (data as { steps?: TimingStep[] }).steps }
    case 'answer':
      return { ...withEvent, answer: data as AnswerPayload }
    case 'error':
      return { ...withEvent, error: data as ErrorPayload }
    case 'done':
      return {
        ...withEvent,
        elapsedMs: (data as { elapsed_ms?: number }).elapsed_ms,
        running: false,
      }
    default:
      return withEvent
  }
}

export function failTurn(turn: Turn, message: string): Turn {
  const error: ErrorPayload = { message }
  return {
    ...turn,
    running: false,
    error,
    events: [...turn.events, { name: 'error', atMs: 0, label: 'Lỗi' }],
  }
}

export function answerText(answer: AnswerPayload | undefined): string | null {
  if (!answer) return null
  const text = answer.text?.trim()
  if (text) return text
  return answer.message?.trim() ?? null
}

export function chartLayout(chart: ChartPayload | undefined): Record<string, unknown> {
  return {
    autosize: true,
    margin: { t: 24, r: 16, b: 44, l: 60 },
    font: { family: 'Inter, system-ui, sans-serif', size: 12, color: '#16181d' },
    paper_bgcolor: 'transparent',
    plot_bgcolor: 'transparent',
    ...(chart?.spec.layout ?? {}),
  }
}
