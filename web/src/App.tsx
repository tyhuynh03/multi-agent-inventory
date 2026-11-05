import { useCallback, useEffect, useRef, useState } from 'react'
import { streamChat } from './api'
import AskBar from './components/AskBar'
import HealthBadge from './components/HealthBadge'
import SchemaPanel from './components/SchemaPanel'
import SqlConsole from './components/SqlConsole'
import TurnCard from './components/TurnCard'
import { createTurn, failTurn, reduceTurn } from './turnReducer'
import type { Turn } from './types'

type Tab = 'chat' | 'sql' | 'schema'

const TABS: { id: Tab; label: string }[] = [
  { id: 'chat', label: 'Hỏi đáp' },
  { id: 'sql', label: 'SQL console' },
  { id: 'schema', label: 'Lược đồ' },
]

export default function App() {
  const [tab, setTab] = useState<Tab>('chat')
  const [turns, setTurns] = useState<Turn[]>([])
  const [running, setRunning] = useState(false)
  const abortRef = useRef<AbortController | null>(null)
  const nextId = useRef(1)
  const bottomRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [turns])

  const ask = useCallback(async (question: string) => {
    const id = nextId.current
    nextId.current += 1

    setTurns((previous) => [...previous, createTurn(id, question)])
    setRunning(true)

    const controller = new AbortController()
    abortRef.current = controller
    const startedAt = performance.now()

    try {
      await streamChat(
        question,
        (frame) => {
          const atMs = performance.now() - startedAt
          setTurns((previous) =>
            previous.map((turn) => (turn.id === id ? reduceTurn(turn, frame, atMs) : turn)),
          )
        },
        controller.signal,
      )
    } catch (caught) {
      const aborted = caught instanceof DOMException && caught.name === 'AbortError'
      const message = aborted
        ? 'Đã dừng giữa chừng — kết quả chưa hoàn chỉnh'
        : caught instanceof Error
          ? caught.message
          : 'Không gọi được backend'
      setTurns((previous) => previous.map((turn) => (turn.id === id ? failTurn(turn, message) : turn)))
    } finally {
      setRunning(false)
      abortRef.current = null
    }
  }, [])

  return (
    <>
      <header className="app-header">
        <div className="container header-inner">
          <div>
            <h1 className="app-title">Kho hàng — Multi-Agent</h1>
            <p className="app-subtitle">
              Text-to-SQL + RAG + analytics · FastAPI backend, React frontend
            </p>
          </div>
          <HealthBadge />
        </div>
      </header>

      <main className="container pb-5">
        <nav className="tabs">
          {TABS.map((item) => (
            <button
              key={item.id}
              type="button"
              className={`tab${tab === item.id ? ' is-active' : ''}`}
              onClick={() => setTab(item.id)}
            >
              {item.label}
            </button>
          ))}
        </nav>

        {tab === 'chat' && (
          <>
            <AskBar
              running={running}
              onAsk={(question) => void ask(question)}
              onStop={() => abortRef.current?.abort()}
            />
            {turns.length === 0 ? (
              <p className="muted empty-state">
                Chưa có câu hỏi nào. Chọn một ví dụ bên dưới để xem agent chạy từng bước.
              </p>
            ) : (
              <div className="turns">
                {turns.map((turn) => (
                  <TurnCard key={turn.id} turn={turn} />
                ))}
                <div ref={bottomRef} />
              </div>
            )}
            <div className="composer-spacer" />
          </>
        )}
        {tab === 'sql' && <SqlConsole />}
        {tab === 'schema' && <SchemaPanel />}
      </main>
    </>
  )
}
