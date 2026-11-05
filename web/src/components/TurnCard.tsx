import { Suspense, lazy } from 'react'
import { formatMs } from '../format'
import { answerText } from '../turnReducer'
import ResultTable from './ResultTable'
import StepTimeline from './StepTimeline'
import type { Turn } from '../types'

// Plotly ~4MB: chỉ tải khi thực sự có biểu đồ.
const ChartPanel = lazy(() => import('./ChartPanel'))

export default function TurnCard({ turn }: { turn: Turn }) {
  const answer = answerText(turn.answer)

  return (
    <article className={`turn${turn.running ? ' is-running' : ''}`}>
      <header className="turn-head">
        <h3 className="turn-question">{turn.question}</h3>
        {turn.elapsedMs !== undefined && (
          <span className="turn-time">{formatMs(turn.elapsedMs)}</span>
        )}
      </header>

      <StepTimeline events={turn.events} running={turn.running} />

      {turn.error && (
        <div className="error-box">
          <strong>{turn.error.type ?? 'pipeline_error'}</strong>
          <p>{turn.error.message}</p>
          {turn.error.sql && <pre className="code">{turn.error.sql}</pre>}
        </div>
      )}

      {answer && !turn.error && <p className="turn-answer">{answer}</p>}

      {turn.sql && turn.sql !== 'Schema Information' && (
        <details className="sql-block" open={Boolean(turn.error)}>
          <summary>SQL do agent sinh</summary>
          <pre className="code">{turn.sql}</pre>
        </details>
      )}

      {turn.table && <ResultTable table={turn.table} />}
      {turn.chart && (
        <Suspense fallback={<p className="muted">Đang tải thư viện biểu đồ…</p>}>
          <ChartPanel chart={turn.chart} />
        </Suspense>
      )}
      {turn.schemaMarkdown && <pre className="code">{turn.schemaMarkdown}</pre>}
    </article>
  )
}
