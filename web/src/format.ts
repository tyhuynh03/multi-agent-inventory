export function formatCell(value: unknown): string {
  if (value === null || value === undefined || value === '') return '—'
  if (typeof value === 'boolean') return value ? 'true' : 'false'
  if (typeof value === 'number') {
    return Number.isInteger(value)
      ? value.toLocaleString('en-US')
      : value.toLocaleString('en-US', { maximumFractionDigits: 2 })
  }
  if (typeof value === 'string') {
    // Timestamp từ Postgres/ISO: bỏ múi giờ và phần thừa cho gọn bảng.
    const iso = value.match(/^(\d{4}-\d{2}-\d{2})[T ](\d{2}:\d{2})/)
    if (iso) return `${iso[2]} ${iso[1].slice(5)}`
    return value
  }
  return String(value)
}

export function formatMs(value: number): string {
  if (value < 1000) return `${Math.round(value)}ms`
  return `${(value / 1000).toFixed(1)}s`
}
