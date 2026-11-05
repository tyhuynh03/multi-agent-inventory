import type { HealthResponse, SchemaTable, SseFrame, SqlConsoleResponse } from './types'

export class ApiError extends Error {}

function readDetail(body: string): string | null {
  try {
    const parsed = JSON.parse(body) as { detail?: unknown }
    if (typeof parsed.detail === 'string') return parsed.detail
    if (parsed.detail && typeof parsed.detail === 'object') return JSON.stringify(parsed.detail)
  } catch {
    // body không phải JSON
  }
  return null
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, init)
  if (!response.ok) {
    throw new ApiError(readDetail(await response.text()) ?? `HTTP ${response.status}`)
  }
  return (await response.json()) as T
}

export function getHealth(): Promise<HealthResponse> {
  return request<HealthResponse>('/api/health')
}

export function getSchema(): Promise<SchemaTable[]> {
  return request<SchemaTable[]>('/api/schema')
}

export function runSql(sql: string): Promise<SqlConsoleResponse> {
  return request<SqlConsoleResponse>('/api/sql', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ sql }),
  })
}

function parseFrame(raw: string): SseFrame | null {
  let name = 'message'
  const dataLines: string[] = []

  for (const line of raw.split('\n')) {
    if (line.startsWith(':')) continue
    if (line.startsWith('event:')) name = line.slice(6).trim()
    else if (line.startsWith('data:')) dataLines.push(line.slice(5).replace(/^ /, ''))
  }

  if (dataLines.length === 0) return null
  try {
    return { name, data: JSON.parse(dataLines.join('\n')) as unknown }
  } catch {
    return null
  }
}

export async function streamChat(
  question: string,
  onFrame: (frame: SseFrame) => void,
  signal: AbortSignal,
): Promise<void> {
  const response = await fetch('/api/chat/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question }),
    signal,
  })

  if (!response.ok) {
    throw new ApiError(readDetail(await response.text()) ?? `HTTP ${response.status}`)
  }
  if (!response.body) {
    throw new ApiError('Trình duyệt không trả về được streaming body')
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  for (;;) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })

    let boundary = buffer.indexOf('\n\n')
    while (boundary !== -1) {
      const frame = parseFrame(buffer.slice(0, boundary))
      buffer = buffer.slice(boundary + 2)
      if (frame) onFrame(frame)
      boundary = buffer.indexOf('\n\n')
    }
  }
}
