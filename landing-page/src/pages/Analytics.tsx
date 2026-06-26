import { useState, useEffect, useMemo } from "react"
import { useAuth } from "../context/AuthContext"
import { API_BASE, getAuthHeaders } from "../lib/api"
import { Loader2, Download } from "lucide-react"
import { Button } from "../components/ui/button"

export function AnalyticsPage() {
  const { user } = useAuth()
  const [stats, setStats] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [range, setRange] = useState<7 | 30 | 90 | 0>(0) // 0 = all time

  useEffect(() => {
    if (!user) return
    Promise.all([
      fetch(`${API_BASE}/api/v1/community-stats`).then(r => r.ok ? r.json() : null),
      fetch(`${API_BASE}/api/v1/history?limit=500`, { headers: getAuthHeaders() }).then(r => r.ok ? r.json() : null),
    ]).then(([community, history]) => {
      // Backend returns { items: [...] } with fields: preview, date, red_flags
      // Normalize to text_preview, timestamp, red_flag_score for UI consistency
      const rows = history?.items ?? history?.analyses ?? history ?? []
      const normalized = rows.map((h: any) => ({
        ...h,
        text_preview: h.text_preview ?? h.preview ?? "",
        timestamp: h.timestamp ?? h.date ?? h.created_at ?? "",
        red_flag_score: h.red_flag_score ?? (typeof h.red_flags === 'number' ? h.red_flags / 100 : 0),
      }))
      setStats({ community, history: normalized })
    }).catch(() => {}).finally(() => setLoading(false))
  }, [user])

  if (!user) return <div className="min-h-screen bg-background flex items-center justify-center text-foreground"><p>Please sign in.</p></div>
  if (loading) return <div className="min-h-screen bg-background flex items-center justify-center"><Loader2 className="w-6 h-6 animate-spin text-primary" /></div>

  const allHistory = stats?.history || []

  // date-filtered history
  const filtered = useMemo(() => {
    if (range === 0) return allHistory
    const cutoff = new Date(); cutoff.setDate(cutoff.getDate() - range)
    return allHistory.filter((h: any) => h.timestamp && new Date(h.timestamp) >= cutoff)
  }, [allHistory, range])

  const totalAnalyzed = stats?.community?.total_analyses ?? filtered.length
  const fakeCount = filtered.filter((h: any) => h.prediction === "FAKE").length
  const realCount = filtered.filter((h: any) => h.prediction === "REAL").length
  const avgConf = filtered.length > 0 ? (filtered.reduce((s: number, h: any) => s + (h.confidence || 0), 0) / filtered.length).toFixed(1) : "0"
  const total = realCount + fakeCount || 1

  // topic breakdown from text previews
  const topicMap = useMemo(() => {
    const topics: Record<string, { real: number; fake: number }> = {
      "Politics": { real: 0, fake: 0 },
      "Health": { real: 0, fake: 0 },
      "Technology": { real: 0, fake: 0 },
      "Finance": { real: 0, fake: 0 },
      "Social Media": { real: 0, fake: 0 },
      "Other": { real: 0, fake: 0 },
    }
    const rules: [string, RegExp][] = [
      ["Politics", /politic|election|govern|minister|parliament|congress|bjp|aap|vote|democrat|republican/i],
      ["Health", /health|covid|vaccine|hospital|doctor|medical|disease|virus|cure|patient/i],
      ["Technology", /tech|ai|software|google|apple|microsoft|crypto|bitcoin|startup|hack/i],
      ["Finance", /bank|stock|market|invest|rupee|dollar|economy|gdp|inflation|rbi|tax/i],
      ["Social Media", /whatsapp|facebook|instagram|twitter|tiktok|youtube|viral|forward|share/i],
    ]
    filtered.forEach((h: any) => {
      const txt = h.text_preview || h.preview || ""
      const pred = h.prediction === "FAKE" ? "fake" : "real"
      let matched = false
      for (const [topic, re] of rules) {
        if (re.test(txt)) { topics[topic][pred]++; matched = true; break }
      }
      if (!matched) topics["Other"][pred]++
    })
    return Object.entries(topics).filter(([, v]) => v.real + v.fake > 0)
  }, [filtered])

  return (
    <div className="bg-background p-6 md:p-8 text-foreground">
      <div className="max-w-5xl mx-auto">
        <div className="flex justify-between items-start mb-8 flex-wrap gap-4">
          <div>
            <h1 className="text-2xl font-heading font-extrabold tracking-tight mb-2">Analytics Overview</h1>
            <p className="text-muted-foreground text-sm">Forensic metrics for the current verification cycle.</p>
          </div>
          {/* Date range + Export */}
          <div className="flex gap-2 items-center flex-wrap">
            {([
              [7, "7D"], [30, "30D"], [90, "90D"], [0, "All"]
            ] as [number, string][]).map(([v, label]) => (
              <button key={v} onClick={() => setRange(v as any)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${range === v ? "bg-primary/15 border-primary/40 text-primary" : "border-border text-muted-foreground hover:text-foreground"}`}>
                {label}
              </button>
            ))}
            <Button variant="outline" size="sm" onClick={() => {
              const report = { generated: new Date().toISOString(), range: range || 'all', totalAnalyzed: range === 0 ? totalAnalyzed : filtered.length, fakeCount, realCount, avgConfidence: avgConf, topics: Object.fromEntries(topicMap), recentAnalyses: filtered.slice(0, 50) }
              const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' })
              const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = 'verifai-analytics.json'; a.click()
            }}>
              <Download className="w-3.5 h-3.5 mr-1.5" /> Export
            </Button>
          </div>
        </div>

        {/* Stat cards */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8 stagger-children">
          {[
            { label: "TOTAL ANALYZED", value: range === 0 ? totalAnalyzed : filtered.length, dot: "bg-[#4ADE80]" },
            { label: "AVG CONFIDENCE", value: `${avgConf}%`, dot: "bg-[#38bdf8]" },
            { label: "FAKE DETECTED", value: fakeCount, dot: "bg-destructive" },
          ].map((s, i) => (
            <div key={i} className="card-enterprise p-5 fade-up-stagger">
              <div className="flex items-center gap-2 mb-2">
                <span className={`w-2 h-2 rounded-full ${s.dot}`} />
                <span className="text-[10px] text-muted-foreground uppercase tracking-widest font-mono">{s.label}</span>
              </div>
              <div className="text-2xl font-heading font-bold">{s.value}</div>
            </div>
          ))}
        </div>

        {/* Prediction distribution bar */}
        <div className="card-enterprise p-5 mb-8">
          <h3 className="text-sm font-semibold mb-4">Prediction Distribution</h3>
          <div className="flex h-8 rounded-lg overflow-hidden">
            <div className="bg-[#4ADE80] transition-all duration-500 flex items-center justify-center text-xs font-bold text-background"
              style={{ width: `${(realCount / total) * 100}%` }}>{realCount > 0 && `REAL ${realCount}`}</div>
            <div className="bg-destructive transition-all duration-500 flex items-center justify-center text-xs font-bold text-white"
              style={{ width: `${(fakeCount / total) * 100}%` }}>{fakeCount > 0 && `FAKE ${fakeCount}`}</div>
          </div>
          <div className="flex justify-between mt-2 text-[10px] text-muted-foreground">
            <span>Real: {((realCount / total) * 100).toFixed(0)}%</span>
            <span>Fake: {((fakeCount / total) * 100).toFixed(0)}%</span>
          </div>
        </div>

        {/* Topic Breakdown */}
        <div className="card-enterprise p-5 mb-8">
          <h3 className="text-sm font-semibold mb-4">Topic Breakdown</h3>
          <div className="space-y-3">
            {topicMap.map(([topic, counts]) => {
              const topicTotal = counts.real + counts.fake
              const maxBar = Math.max(...topicMap.map(([, c]) => c.real + c.fake)) || 1
              return (
                <div key={topic}>
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-foreground font-medium">{topic}</span>
                    <span className="text-muted-foreground">{topicTotal} ({counts.fake} fake)</span>
                  </div>
                  <div className="flex h-3 rounded overflow-hidden bg-background">
                    <div className="bg-[#4ADE80] transition-all duration-500" style={{ width: `${(counts.real / maxBar) * 100}%` }} />
                    <div className="bg-destructive transition-all duration-500" style={{ width: `${(counts.fake / maxBar) * 100}%` }} />
                  </div>
                </div>
              )
            })}
            {topicMap.length === 0 && <p className="text-xs text-muted-foreground text-center py-4">No data yet. Analyze articles to see topic breakdown.</p>}
          </div>
        </div>

        {/* Activity Trend */}
        {(() => {
          const days = range === 0 ? 30 : range
          const buckets: { date: string; real: number; fake: number }[] = []
          for (let i = days - 1; i >= 0; i--) {
            const d = new Date(); d.setDate(d.getDate() - i)
            const key = d.toISOString().split("T")[0]
            buckets.push({ date: key, real: 0, fake: 0 })
          }
          filtered.forEach((h: any) => {
            const key = h.timestamp?.split("T")[0]
            const b = buckets.find(x => x.date === key)
            if (b) h.prediction === "FAKE" ? b.fake++ : b.real++
          })
          const maxVal = Math.max(...buckets.map(b => b.real + b.fake), 1)
          const chartH = 120
          const barW = Math.max(4, Math.min(16, Math.floor(600 / buckets.length) - 2))

          return (
            <div className="card-enterprise p-5 mb-8">
              <h3 className="text-sm font-semibold mb-4">Activity Trend</h3>
              <div className="overflow-x-auto">
                <svg width={buckets.length * (barW + 2) + 40} height={chartH + 30} className="min-w-full">
                  {/* Y-axis labels */}
                  <text x="0" y="12" className="fill-muted-foreground" fontSize="9">{maxVal}</text>
                  <text x="0" y={chartH / 2 + 4} className="fill-muted-foreground" fontSize="9">{Math.round(maxVal / 2)}</text>
                  <text x="0" y={chartH} className="fill-muted-foreground" fontSize="9">0</text>
                  {/* Grid lines */}
                  <line x1="28" y1="0" x2={buckets.length * (barW + 2) + 32} y2="0" stroke="hsl(var(--border))" strokeWidth="0.5" />
                  <line x1="28" y1={chartH / 2} x2={buckets.length * (barW + 2) + 32} y2={chartH / 2} stroke="hsl(var(--border))" strokeWidth="0.5" strokeDasharray="4" />
                  {/* Bars */}
                  {buckets.map((b, i) => {
                    const total = b.real + b.fake
                    const h = (total / maxVal) * chartH
                    const realH = total > 0 ? (b.real / total) * h : 0
                    const fakeH = h - realH
                    const x = 30 + i * (barW + 2)
                    return (
                      <g key={i}>
                        <title>{b.date}: {b.real} real, {b.fake} fake</title>
                        <rect x={x} y={chartH - h} width={barW} height={realH} rx="1" fill="#4ADE80" opacity="0.85" />
                        <rect x={x} y={chartH - fakeH} width={barW} height={fakeH} rx="1" fill="hsl(var(--destructive))" opacity="0.85" />
                        {/* Show date label for first, last, and every 7th */}
                        {(i === 0 || i === buckets.length - 1 || i % 7 === 0) && (
                          <text x={x + barW / 2} y={chartH + 14} textAnchor="middle" className="fill-muted-foreground" fontSize="8">
                            {b.date.slice(5)}
                          </text>
                        )}
                      </g>
                    )
                  })}
                </svg>
              </div>
              <div className="flex items-center gap-4 mt-3">
                <span className="flex items-center gap-1.5 text-[10px] text-muted-foreground"><span className="w-2.5 h-2.5 rounded-sm bg-[#4ADE80]" /> Real</span>
                <span className="flex items-center gap-1.5 text-[10px] text-muted-foreground"><span className="w-2.5 h-2.5 rounded-sm bg-destructive" /> Fake</span>
              </div>
            </div>
          )
        })()}

        {/* Recent analyses table */}
        <div className="bg-secondary border border-border rounded-xl overflow-hidden">
          <div className="p-5 border-b border-border"><h3 className="text-sm font-semibold">Recent Analyses</h3></div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead><tr className="border-b border-border bg-background/50">
                <th className="text-left p-3 text-xs text-muted-foreground font-medium">Date</th>
                <th className="text-left p-3 text-xs text-muted-foreground font-medium">Prediction</th>
                <th className="text-left p-3 text-xs text-muted-foreground font-medium">Confidence</th>
                <th className="text-left p-3 text-xs text-muted-foreground font-medium">Preview</th>
              </tr></thead>
              <tbody>
                {filtered.slice(0, 20).map((h: any, i: number) => (
                  <tr key={i} className="border-b border-border/50 hover:bg-background/30">
                    <td className="p-3 text-xs text-muted-foreground">{h.timestamp?.split("T")[0] ?? "—"}</td>
                    <td className="p-3"><span className={`text-xs font-medium px-2 py-0.5 rounded-full ${h.prediction === "FAKE" ? "bg-destructive/15 text-destructive" : "bg-[#4ADE80]/15 text-[#4ADE80]"}`}>{h.prediction}</span></td>
                    <td className="p-3 text-xs">{h.confidence?.toFixed(1) ?? 0}%</td>
                    <td className="p-3 text-xs max-w-[250px] truncate text-muted-foreground">{h.text_preview ?? h.preview ?? "—"}</td>
                  </tr>
                ))}
                {filtered.length === 0 && <tr><td colSpan={4} className="p-6 text-center text-xs text-muted-foreground">No analyses in this time range.</td></tr>}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  )
}
