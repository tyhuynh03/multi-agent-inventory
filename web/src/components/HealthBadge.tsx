import { useEffect, useState } from 'react'
import { getHealth } from '../api'
import type { HealthResponse } from '../types'

export default function HealthBadge() {
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [refreshing, setRefreshing] = useState(false)

  useEffect(() => {
    let active = true
    getHealth()
      .then((data) => {
        if (active) setHealth(data)
      })
      .catch((caught: unknown) => {
        if (active) setError(caught instanceof Error ? caught.message : 'Không gọi được backend')
      })
    return () => {
      active = false
    }
  }, [])

  async function refresh() {
    setRefreshing(true)
    try {
      setHealth(await getHealth())
      setError(null)
    } catch (caught) {
      setHealth(null)
      setError(caught instanceof Error ? caught.message : 'Không gọi được backend')
    } finally {
      setRefreshing(false)
    }
  }

  const state = error ? 'is-bad' : health?.status === 'ok' ? 'is-ok' : ''
  const text = error
    ? 'Backend offline'
    : !health
      ? 'Đang kiểm tra…'
      : health.status === 'ok'
        ? `${health.db.tables?.length ?? 0} bảng · ${health.model}`
        : 'Database lỗi'

  return (
    <div className="health">
      <div className="health-row">
        <span className={`status ${state}`}>
          <span className="status-dot" />
          <span>{text}</span>
        </span>
        <button type="button" className="btn-ghost" disabled={refreshing} onClick={() => void refresh()}>
          {refreshing ? 'Đang kiểm tra…' : 'Kiểm tra lại'}
        </button>
      </div>
      {error && (
        <p className="warn">
          {error}. Khởi động: uvicorn backend.app.main:app --reload --port 8000
        </p>
      )}
      {health && !health.ai_pipeline.groq_api_key_configured && (
        <p className="warn">GROQ_API_KEY chưa đặt — tab Hỏi đáp sẽ lỗi, SQL console vẫn chạy được.</p>
      )}
      {health && !health.db.ok && <p className="warn">{health.db.error}</p>}
    </div>
  )
}
