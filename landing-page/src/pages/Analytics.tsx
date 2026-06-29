import { useState, useEffect, useMemo } from "react"
import { useAuth } from "../context/AuthContext"
import { API_BASE, getAuthHeaders } from "../lib/api"
import { Loader2, Download, TrendingUp, TrendingDown, BarChart3, PieChart, Activity, Target } from "lucide-react"
import { Button } from "../components/ui/button"

export function AnalyticsPage() {
  const { user } = useAuth()
  const [stats, setStats] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [range, setRange] = useState<7 | 30 | 90 | 0>(0)

  useEffect(() => {
    if (!user) return
    Promise.all([
      fetch(`${API_BASE}/api/v1/community-stats`).then(r => r.ok ? r.json() : null),
      fetch(`${API_BASE}/api/v1/user/history?limit=500`, { headers: getAuthHeaders() }).then(r => r.ok ? r.json() : null),
    ]).then(([community, history]) => {
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

  const allHistory = stats?.history || []

  const filtered = useMemo(() => {
    if (range === 0) return allHistory
    const cutoff = new Date(); cutoff.setDate(cutoff.getDate() - range)
    return allHistory.filter((h: any) => h.timestamp && new Date(h.timestamp) >= cutoff)
  }, [allHistory, range])

  const totalAnalyzed = filtered.length
  const fakeCount = filtered.filter((h: any) => h.prediction === "FAKE").length
  const realCount = filtered.filter((h: any) => h.prediction === "REAL").length
  const avgConf = filtered.length > 0 ? (filtered.reduce((s: number, h: any) => s + (h.confidence || 0), 0) / filtered.length) : 0
  const total = realCount + fakeCount || 1
  const fakePercent = ((fakeCount / total) * 100).toFixed(1)
  const realPercent = ((realCount / total) * 100).toFixed(1)

  // Confidence distribution buckets
  const confBuckets = useMemo(() => {
    const buckets = [
      { label: "50-60%", min: 50, max: 60, count: 0 },
      { label: "60-70%", min: 60, max: 70, count: 0 },
      { label: "70-80%", min: 70, max: 80, count: 0 },
      { label: "80-90%", min: 80, max: 90, count: 0 },
      { label: "90-100%", min: 90, max: 101, count: 0 },
    ]
    filtered.forEach((h: any) => {
      const c = h.confidence || 0
      const b = buckets.find(b => c >= b.min && c < b.max)
      if (b) b.count++
    })
    return buckets
  }, [filtered])

  // Topic breakdown
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

  // Loading guard after all hooks
  if (loading) return <div className="min-h-screen bg-background flex items-center justify-center"><Loader2 className="w-6 h-6 animate-spin text-primary" /></div>

  // SVG Donut chart helper
  const DonutChart = () => {
    const size = 140, cx = size / 2, cy = size / 2, r = 50, stroke = 14
    const circumference = 2 * Math.PI * r
    const realArc = (realCount / total) * circumference
    const fakeArc = (fakeCount / total) * circumference
    return (
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        <circle cx={cx} cy={cy} r={r} fill="none" stroke="hsl(var(--border))" strokeWidth={stroke} opacity="0.3" />
        <circle cx={cx} cy={cy} r={r} fill="none" stroke="#4ADE80" strokeWidth={stroke}
          strokeDasharray={`${realArc} ${circumference}`} strokeDashoffset="0"
          transform={`rotate(-90 ${cx} ${cy})`} strokeLinecap="round" className="transition-all duration-700" />
        <circle cx={cx} cy={cy} r={r} fill="none" stroke="hsl(var(--destructive))" strokeWidth={stroke}
          strokeDasharray={`${fakeArc} ${circumference}`} strokeDashoffset={`-${realArc}`}
          transform={`rotate(-90 ${cx} ${cy})`} strokeLinecap="round" className="transition-all duration-700" />
        <text x={cx} y={cy - 6} textAnchor="middle" className="fill-foreground text-2xl font-bold" fontSize="22">{total}</text>
        <text x={cx} y={cy + 12} textAnchor="middle" className="fill-muted-foreground" fontSize="10">Total</text>
      </svg>
    )
  }

  return (
    <div className="bg-background p-6 md:p-8 text-foreground">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="flex justify-between items-start mb-8 flex-wrap gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <BarChart3 className="w-5 h-5 text-primary" />
              <h1 className="text-2xl font-heading font-extrabold tracking-tight">Analytics</h1>
            </div>
            <p className="text-muted-foreground text-sm">Deep insights into your verification activity and detection patterns.</p>
          </div>
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
              const report = { generated: new Date().toISOString(), range: range || 'all', totalAnalyzed, fakeCount, realCount, avgConfidence: avgConf.toFixed(1), topics: Object.fromEntries(topicMap) }
              const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' })
              const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = 'verifai-analytics.json'; a.click()
            }}>
              <Download className="w-3.5 h-3.5 mr-1.5" /> Export
            </Button>
          </div>
        </div>

        {/* Stat Cards */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8 stagger-children">
          {[
            { label: "ARTICLES ANALYZED", value: totalAnalyzed, icon: <Activity className="w-4 h-4" />, color: "text-primary bg-primary/10", trend: totalAnalyzed > 0 ? "up" : null },
            { label: "FAKE DETECTED", value: fakeCount, icon: <TrendingDown className="w-4 h-4" />, color: "text-destructive bg-destructive/10", trend: fakeCount > 0 ? "alert" : null },
            { label: "VERIFIED REAL", value: realCount, icon: <TrendingUp className="w-4 h-4" />, color: "text-[#4ADE80] bg-[#4ADE80]/10", trend: realCount > 0 ? "up" : null },
            { label: "AVG CONFIDENCE", value: `${avgConf.toFixed(1)}%`, icon: <Target className="w-4 h-4" />, color: "text-accent bg-accent/10", trend: avgConf >= 80 ? "up" : avgConf > 0 ? "mid" : null },
          ].map((s, i) => (
            <div key={i} className="card-enterprise p-5 fade-up-stagger">
              <div className="flex items-center justify-between mb-3">
                <div className={`w-9 h-9 rounded-xl flex items-center justify-center ${s.color}`}>{s.icon}</div>
                {s.trend === "up" && <span className="text-[10px] text-[#4ADE80] bg-[#4ADE80]/10 px-2 py-0.5 rounded-full font-medium">● Active</span>}
                {s.trend === "alert" && <span className="text-[10px] text-destructive bg-destructive/10 px-2 py-0.5 rounded-full font-medium">⚠ Alert</span>}
              </div>
              <div className="text-2xl font-heading font-bold">{s.value}</div>
              <div className="text-[10px] text-muted-foreground font-mono uppercase tracking-widest mt-1">{s.label}</div>
            </div>
          ))}
        </div>

        {/* Main Charts Row */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">

          {/* Prediction Distribution Donut */}
          <div className="card-enterprise p-6">
            <div className="flex items-center gap-2 mb-5">
              <PieChart className="w-4 h-4 text-primary" />
              <h3 className="text-sm font-semibold">Prediction Distribution</h3>
            </div>
            <div className="flex items-center justify-center gap-8">
              <DonutChart />
              <div className="space-y-4">
                <div className="flex items-center gap-3">
                  <span className="w-3 h-3 rounded-full bg-[#4ADE80]" />
                  <div>
                    <div className="text-lg font-bold text-foreground">{realPercent}%</div>
                    <div className="text-[10px] text-muted-foreground font-mono uppercase">Real ({realCount})</div>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <span className="w-3 h-3 rounded-full bg-destructive" />
                  <div>
                    <div className="text-lg font-bold text-foreground">{fakePercent}%</div>
                    <div className="text-[10px] text-muted-foreground font-mono uppercase">Fake ({fakeCount})</div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Confidence Distribution Histogram */}
          <div className="card-enterprise p-6">
            <div className="flex items-center gap-2 mb-5">
              <BarChart3 className="w-4 h-4 text-accent" />
              <h3 className="text-sm font-semibold">Confidence Distribution</h3>
            </div>
            {(() => {
              const maxCount = Math.max(...confBuckets.map(b => b.count), 1)
              const barH = 100
              return (
                <div className="flex items-end justify-around gap-2" style={{ height: barH + 30 }}>
                  {confBuckets.map((b, i) => {
                    const h = (b.count / maxCount) * barH
                    return (
                      <div key={i} className="flex flex-col items-center gap-1 flex-1">
                        <span className="text-[10px] text-muted-foreground font-mono">{b.count}</span>
                        <div className="w-full rounded-t-md bg-gradient-to-t from-primary/80 to-accent/80 transition-all duration-500 hover:opacity-80"
                          style={{ height: Math.max(h, 2) }} title={`${b.label}: ${b.count} analyses`} />
                        <span className="text-[9px] text-muted-foreground font-mono">{b.label}</span>
                      </div>
                    )
                  })}
                </div>
              )
            })()}
            {filtered.length === 0 && <p className="text-xs text-muted-foreground text-center py-8">No data yet.</p>}
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
            <div className="card-enterprise p-6 mb-8">
              <div className="flex items-center justify-between mb-5">
                <div className="flex items-center gap-2">
                  <Activity className="w-4 h-4 text-primary" />
                  <h3 className="text-sm font-semibold">Activity Trend</h3>
                </div>
                <div className="flex items-center gap-4">
                  <span className="flex items-center gap-1.5 text-[10px] text-muted-foreground"><span className="w-2.5 h-2.5 rounded-sm bg-[#4ADE80]" /> Real</span>
                  <span className="flex items-center gap-1.5 text-[10px] text-muted-foreground"><span className="w-2.5 h-2.5 rounded-sm bg-destructive" /> Fake</span>
                </div>
              </div>
              <div className="overflow-x-auto">
                <svg width={buckets.length * (barW + 2) + 40} height={chartH + 30} className="min-w-full">
                  <text x="0" y="12" className="fill-muted-foreground" fontSize="9">{maxVal}</text>
                  <text x="0" y={chartH / 2 + 4} className="fill-muted-foreground" fontSize="9">{Math.round(maxVal / 2)}</text>
                  <text x="0" y={chartH} className="fill-muted-foreground" fontSize="9">0</text>
                  <line x1="28" y1="0" x2={buckets.length * (barW + 2) + 32} y2="0" stroke="hsl(var(--border))" strokeWidth="0.5" />
                  <line x1="28" y1={chartH / 2} x2={buckets.length * (barW + 2) + 32} y2={chartH / 2} stroke="hsl(var(--border))" strokeWidth="0.5" strokeDasharray="4" />
                  {buckets.map((b, i) => {
                    const bTotal = b.real + b.fake
                    const h = (bTotal / maxVal) * chartH
                    const realH = bTotal > 0 ? (b.real / bTotal) * h : 0
                    const fakeH = h - realH
                    const x = 30 + i * (barW + 2)
                    return (
                      <g key={i}>
                        <title>{b.date}: {b.real} real, {b.fake} fake</title>
                        <rect x={x} y={chartH - h} width={barW} height={realH} rx="1" fill="#4ADE80" opacity="0.85" />
                        <rect x={x} y={chartH - fakeH} width={barW} height={fakeH} rx="1" fill="hsl(var(--destructive))" opacity="0.85" />
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
            </div>
          )
        })()}

        {/* Bottom Row: Topic Breakdown + Accuracy Metrics */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

          {/* Topic Breakdown */}
          <div className="card-enterprise p-6">
            <div className="flex items-center gap-2 mb-5">
              <BarChart3 className="w-4 h-4 text-primary" />
              <h3 className="text-sm font-semibold">Topic Breakdown</h3>
            </div>
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

          {/* Detection Metrics */}
          <div className="card-enterprise p-6">
            <div className="flex items-center gap-2 mb-5">
              <Target className="w-4 h-4 text-accent" />
              <h3 className="text-sm font-semibold">Detection Metrics</h3>
            </div>
            <div className="space-y-4">
              {[
                { label: "Fake Detection Rate", value: `${fakePercent}%`, desc: "Percentage of articles classified as fake", bar: parseFloat(fakePercent), color: "bg-destructive" },
                { label: "Real Verification Rate", value: `${realPercent}%`, desc: "Percentage of articles verified as real", bar: parseFloat(realPercent), color: "bg-[#4ADE80]" },
                { label: "Average Confidence", value: `${avgConf.toFixed(1)}%`, desc: "Mean confidence across all predictions", bar: avgConf, color: "bg-accent" },
                { label: "High Confidence (>90%)", value: `${filtered.length > 0 ? ((filtered.filter((h: any) => (h.confidence || 0) >= 90).length / filtered.length) * 100).toFixed(1) : 0}%`, desc: "Analyses with confidence above 90%", bar: filtered.length > 0 ? (filtered.filter((h: any) => (h.confidence || 0) >= 90).length / filtered.length) * 100 : 0, color: "bg-primary" },
              ].map((m, i) => (
                <div key={i}>
                  <div className="flex justify-between items-baseline mb-1">
                    <span className="text-xs font-medium text-foreground">{m.label}</span>
                    <span className="text-sm font-bold font-heading">{m.value}</span>
                  </div>
                  <div className="h-2 rounded-full bg-background overflow-hidden">
                    <div className={`h-full rounded-full ${m.color} transition-all duration-700`} style={{ width: `${Math.min(m.bar, 100)}%` }} />
                  </div>
                  <p className="text-[10px] text-muted-foreground mt-0.5">{m.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
