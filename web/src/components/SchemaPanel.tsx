import { useEffect, useState } from 'react'
import { getSchema } from '../api'
import type { SchemaTable } from '../types'

export default function SchemaPanel() {
  const [tables, setTables] = useState<SchemaTable[]>([])
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let active = true
    getSchema()
      .then((data) => {
        if (active) setTables(data)
      })
      .catch((caught: unknown) => {
        if (active) setError(caught instanceof Error ? caught.message : 'Không đọc được schema')
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
  }, [])

  return (
    <section className="panel">
      <div className="panel-head">
        <h2 className="panel-title">Lược đồ database</h2>
        <span className="panel-meta">{tables.length} bảng</span>
      </div>
      <div className="panel-body">
        {loading && <p className="muted">Đang đọc information_schema…</p>}
        {error && <div className="error-box"><strong>lỗi</strong><p>{error}</p></div>}
        {!loading && !error && tables.length === 0 && (
          <p className="muted">Database rỗng — chạy migrate_to_postgres.py trước.</p>
        )}
        {tables.map((table) => (
          <details key={table.table} className="schema-table">
            <summary>
              <span className="schema-name">{table.table}</span>
              <span className="panel-meta">{table.columns.length} cột</span>
            </summary>
            <table className="schema-grid">
              <tbody>
                {table.columns.map((column) => (
                  <tr key={column.name}>
                    <td className="col-name">{column.name}</td>
                    <td className="col-type">{column.type}</td>
                    <td className="col-null">{column.nullable ? 'NULL' : 'NOT NULL'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </details>
        ))}
      </div>
    </section>
  )
}
