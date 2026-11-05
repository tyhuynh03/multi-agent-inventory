import { useEffect, useRef, useState } from 'react'
import Plotly from 'plotly.js-dist-min'
import { chartLayout } from '../turnReducer'
import type { ChartPayload } from '../types'

export default function ChartPanel({ chart }: { chart: ChartPayload }) {
  const hostRef = useRef<HTMLDivElement | null>(null)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    const element = hostRef.current
    if (!element || !chart.spec?.data) return

    setFailed(false)
    Plotly.newPlot(element, chart.spec.data, chartLayout(chart), {
      responsive: true,
      displayModeBar: false,
    }).catch(() => setFailed(true))

    return () => {
      Plotly.purge(element)
    }
  }, [chart])

  if (failed) {
    return <p className="error-box">Không render được biểu đồ: spec trả về không hợp lệ.</p>
  }

  return <div className="chart" ref={hostRef} />
}
