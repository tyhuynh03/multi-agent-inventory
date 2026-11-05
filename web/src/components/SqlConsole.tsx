import { useState } from 'react'
import type { FormEvent } from 'react'
import { runSql } from '../api'
import { formatMs } from '../format'
import ResultTable from './ResultTable'
import type { SqlConsoleResponse } from '../types'

const PRESETS = [
  'SELECT city, province, country FROM warehouses ORDER BY city;',
  'SELECT sku_name, COUNT(*) AS so_don FROM sales s JOIN skus k ON k.sku_id = s.sku_id GROUP BY sku_name ORDER BY so_don DESC LIMIT 10;',
  'SELECT warehouse_id, SUM(revenue) AS revenue FROM sales GROUP BY warehouse_id ORDER BY revenue DESC;',
]

export default function SqlConsole() {
  const [sql, setSql] = useState(PRESETS[0])
  const [result, setResult] = useState<SqlConsoleResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function submit(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    try {
      setResult(await runSql(sql))
    } catch (caught) {
      setResult(null)
      setError(caught instanceof Error ? caught.message : 'Không chạy được truy vấn')
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="panel">
      <div className="panel-head">
        <h2 className="panel-title">SQL console</h2>
        <span className="panel-meta">chỉ SELECT / WITH / EXPLAIN</span>
      </div>
      <div className="panel-body">
        <form onSubmit={submit}>
          <textarea
            className="sql-input"
            value={sql}
            spellCheck={false}
            rows={5}
            onChange={(event) => setSql(event.target.value)}
          />
          <div className="ask-row mt-3">
            <button type="submit" className="btn btn-primary" disabled={busy || sql.trim() === ''}>
              {busy ? 'Đang chạy…' : 'Chạy truy vấn'}
            </button>
            {result && (
              <span className="panel-meta">
                {result.returned_rows} dòng · {formatMs(result.elapsed_ms)}
              </span>
            )}
          </div>
        </form>

        {error && <div className="error-box mt-3"><strong>bị chặn</strong><p>{error}</p></div>}
        {result && <div className="mt-3"><ResultTable table={result} /></div>}

        <div className="examples mt-3">
          {PRESETS.map((preset) => (
            <button key={preset} type="button" className="chip" onClick={() => setSql(preset)}>
              {preset.slice(0, 46)}…
            </button>
          ))}
        </div>
      </div>
    </section>
  )
}
