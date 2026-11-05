import { formatMs } from '../format'
import type { TimelineEvent } from '../types'

interface Props {
  events: TimelineEvent[]
  running: boolean
}

export default function StepTimeline({ events, running }: Props) {
  if (events.length === 0) return null

  return (
    <ol className="timeline">
      {events.map((event, index) => (
        <li
          key={`${event.name}-${index}`}
          className={`timeline-item${event.name === 'error' ? ' is-error' : ''}`}
        >
          <span className="timeline-label">{event.label}</span>
          {event.atMs > 0 && <span className="timeline-time">{formatMs(event.atMs)}</span>}
        </li>
      ))}
      {running && <li className="timeline-item is-pending">Đang chờ bước tiếp theo…</li>}
    </ol>
  )
}
