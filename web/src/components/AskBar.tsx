import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'

const EXAMPLES = [
  'How many warehouses are there?',
  'Top 5 products by revenue',
  'Which products will run out of stock soon?',
  'Show sales by customer type as a bar chart',
]

interface Props {
  running: boolean
  onAsk: (question: string) => void
  onStop: () => void
}

export default function AskBar({ running, onAsk, onStop }: Props) {
  const [value, setValue] = useState('')
  const formRef = useRef<HTMLFormElement | null>(null)
  const inputRef = useRef<HTMLInputElement | null>(null)
  const wasRunning = useRef(false)

  // Composer dính đáy nên phải chừa chỗ đúng bằng chiều cao thật của nó; con số này
  // đổi theo bề ngang màn hình và theo nút "Dừng" chỉ hiện khi đang chạy.
  useEffect(() => {
    const form = formRef.current
    if (!form) return
    const apply = () =>
      document.documentElement.style.setProperty('--composer-h', `${form.offsetHeight}px`)
    apply()
    const observer = new ResizeObserver(apply)
    observer.observe(form)
    return () => observer.disconnect()
  }, [])

  // App tự scroll xuống cuối danh sách khi có kết quả, nên phải đưa con trỏ về ô nhập
  // nếu không người dùng phải cuộn ngược lên để hỏi câu tiếp theo.
  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  useEffect(() => {
    if (wasRunning.current && !running) inputRef.current?.focus()
    wasRunning.current = running
  }, [running])

  function submit(event: FormEvent) {
    event.preventDefault()
    const question = value.trim()
    if (!question || running) return
    onAsk(question)
    setValue('')
  }

  return (
    <form ref={formRef} className="ask-bar" onSubmit={submit}>
      <div className="ask-row">
        <input
          ref={inputRef}
          className="ask-input"
          value={value}
          onChange={(event) => setValue(event.target.value)}
          placeholder="Đặt câu hỏi, ví dụ: top 5 sản phẩm doanh thu cao nhất"
          disabled={running}
          maxLength={600}
        />
        <button type="submit" className="btn btn-primary" disabled={running || value.trim() === ''}>
          {running ? 'Đang chạy…' : 'Hỏi'}
        </button>
        {running && (
          <button type="button" className="btn btn-ghost" onClick={onStop}>
            Dừng
          </button>
        )}
      </div>
      <div className="examples">
        {EXAMPLES.map((example) => (
          <button
            key={example}
            type="button"
            className="chip"
            disabled={running}
            onClick={() => setValue(example)}
          >
            {example}
          </button>
        ))}
      </div>
    </form>
  )
}
