import { formatCell } from '../format'
import type { TablePayload } from '../types'

interface Props {
  table: TablePayload
}

export default function ResultTable({ table }: Props) {
  if (table.columns.length === 0) {
    return <p className="muted">Câu truy vấn không trả về cột nào.</p>
  }

  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            {table.columns.map((column, index) => (
              <th key={`${column}-${index}`}>{column}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {table.rows.length === 0 ? (
            <tr>
              <td className="empty" colSpan={table.columns.length}>
                Không có dòng nào
              </td>
            </tr>
          ) : (
            table.rows.map((row, rowIndex) => (
              <tr key={rowIndex}>
                {row.map((cell, cellIndex) => (
                  <td key={cellIndex}>{formatCell(cell)}</td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
      <p className="table-meta">
        {table.truncated
          ? `${formatCell(table.returned_rows)} dòng — backend đã cắt theo giới hạn, còn nhiều hơn`
          : `${formatCell(table.row_count)} dòng`}
      </p>
    </div>
  )
}
