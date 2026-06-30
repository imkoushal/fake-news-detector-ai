import { useState, useEffect, useMemo } from "react"
import { useAuth } from "../context/AuthContext"
import { API_BASE, getAuthHeaders } from "../lib/api"
import { Link } from "react-router-dom"
import { Loader2, TrendingUp, TrendingDown, BarChart3, PieChart, Activity, Target, Search, ArrowRight, Clock, ShieldCheck } from "lucide-react"

export function Dashboard() {
  const { user } = useAuth()
  const [stats, setStats] = useState<any>(null)
  const [community, setCommunity] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [range, setRange] = useState<7 | 30 | 90 | 0>(0)

  useEffect(() => {
    if (!user) return
    Promise.all([
      fetch(`${API_BASE}/api/v1/community-stats`).then(r => r.ok ? r.json() : null),
      fetch(`${API_BASE}/api/v1/user/history?limit=500`, { headers: getAuthHeaders() }).then(r => r.ok ? r.json() : null),
    ]).then(([comm, history]) => {
      const rows = history?.items ?? history?.analyses ?? history ?? []
      const normalized = rows.map((h: any) => ({
        ...h,
        text_preview: h.text_preview ?? h.preview ?? "",
        timestamp: h.timestamp ?? h.date ?? h.created_at ?? "",
        red_flag_score: h.red_flag_score ?? (typeof h.red_flags === 'number' ? h.red_flags / 100 : 0),
      }))
      setCommunity(comm)
      setStats(normalized)
    }).catch(() => {}).finally(() => setLoading(false))
  }, [user])

  const allHistory = stats || []

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

  const topicMap = useMemo(() => {
    const topics: Record<string, { real: number; fake: number }> = {
      "Politics": { real: 0, fake: 0 }, "Health": { real: 0, fake: 0 },
      "Technology": { real: 0, fake: 0 }, "Finance": { real: 0, fake: 0 },
      "Social Media": { real: 0, fake: 0 }, "Other": { real: 0, fake: 0 },
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

  const greeting = (() => {
    const h = new Date().getHours()
    if (h < 12) return "Good morning"
    if (h < 17) return "Good afternoon"
    return "Good evening"
  })()

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
        <text x={cx} y={cy - 6} textAnchor="middle" className="fill-foreground text-2xl font-bold" fontSize="22">{totalAnalyzed}</text>
        <text x={cx} y={cy + 12} textAnchor="middle" className="fill-muted-foreground" fontSize="10">Total</text>
      </svg>
    )
  }

  const recentFive = allHistory.slice(0, 5)

  return (
    <div className="bg-background p-6 md:p-8 text-foreground">
      <div className="max-w-6xl mx-auto">

        {/* Greeting Header */}
        <div className="card-enterprise p-6 mb-6 relative overflow-hidden">
          <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-primary via-accent to-primary" />
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <h1 className="text-2xl font-heading font-extrabold tracking-tight">{greeting}, {user?.name?.split(" ")[0]}</h1>
              <p className="text-sm text-muted-foreground mt-0.5">Here's your misinformation detection overview.</p>
            </div>
            <div className="flex items-center gap-2">
              <span className="stat-pill"><span className="w-2 h-2 rounded-full bg-[#4ADE80] animate-pulse inline-block mr-1.5" />System Online</span>
              <span className="stat-pill font-mono text-[10px]">{new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}</span>
            </div>
          </div>
        </div>

        {/* Quick Actions */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
          <Link to="/analytics" className="card-enterprise p-5 hover:border-primary/40 transition-all group cursor-pointer">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-primary/10 text-primary flex items-center justify-center"><Search className="w-5 h-5" /></div>
              <div className="flex-1">
                <div className="text-sm font-semibold group-hover:text-primary transition-colors">Analyze Content</div>
                <div className="text-[10px] text-muted-foreground">Check text, URL, or audio</div>
              </div>
              <ArrowRight className="w-4 h-4 text-muted-foreground group-hover:text-primary transition-colors" />
            </div>
          </Link>
          <Link to="/history" className="card-enterprise p-5 hover:border-primary/40 transition-all group cursor-pointer">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-accent/10 text-accent flex items-center justify-center"><Clock className="w-5 h-5" /></div>
              <div className="flex-1">
                <div className="text-sm font-semibold group-hover:text-primary transition-colors">View History</div>
                <div className="text-[10px] text-muted-foreground">{allHistory.length} analyses stored</div>
              </div>
              <ArrowRight className="w-4 h-4 text-muted-foreground group-hover:text-primary transition-colors" />
            </div>
          </Link>
          <Link to="/compare" className="card-enterprise p-5 hover:border-primary/40 transition-all group cursor-pointer">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-[#4ADE80]/10 text-[#4ADE80] flex items-center justify-center"><ShieldCheck className="w-5 h-5" /></div>
              <div className="flex-1">
                <div className="text-sm font-semibold group-hover:text-primary transition-colors">Compare Articles</div>
                <div className="text-[10px] text-muted-foreground">Side-by-side verification</div>
              </div>
              <ArrowRight className="w-4 h-4 text-muted-foreground group-hover:text-primary transition-colors" />
            </div>
          </Link>
        </div>

        {/* Community + User Stat Cards */}
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-widest">Your Statistics</h2>
          <div className="flex gap-1.5">
            {([
              [7, "7D"], [30, "30D"], [90, "90D"], [0, "All"]
            ] as [number, string][]).map(([v, label]) => (
              <button key={v} onClick={() => setRange(v as any)}
                className={`px-2.5 py-1 rounded-lg text-[10px] font-medium border transition-colors ${range === v ? "bg-primary/15 border-primary/40 text-primary" : "border-border text-muted-foreground hover:text-foreground"}`}>
                {label}
              </button>
            ))}
          </div>
        </div>

        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8 stagger-children">
          {[
            { label: "ARTICLES ANALYZED", value: totalAnalyzed, icon: <Activity className="w-4 h-4" />, color: "text-primary bg-primary/10" },
            { label: "FAKE DETECTED", value: fakeCount, icon: <TrendingDown className="w-4 h-4" />, color: "text-destructive bg-destructive/10" },
            { label: "VERIFIED REAL", value: realCount, icon: <TrendingUp className="w-4 h-4" />, color: "text-[#4ADE80] bg-[#4ADE80]/10" },
            { label: "AVG CONFIDENCE", value: `${avgConf.toFixed(1)}%`, icon: <Target className="w-4 h-4" />, color: "text-accent bg-accent/10" },
          ].map((s, i) => (
            <div key={i} className="card-enterprise p-5 fade-up-stagger">
              <div className="flex items-center justify-between mb-3">
                <div className={`w-9 h-9 rounded-xl flex items-center justify-center ${s.color}`}>{s.icon}</div>
              </div>
              <div className="text-2xl font-heading font-bold">{s.value}</div>
              <div className="text-[10px] text-muted-foreground font-mono uppercase tracking-widest mt-1">{s.label}</div>
            </div>
          ))}
        </div>

        {/* Charts Row */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          {/* Donut */}
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
                    <div className="text-lg font-bold">{realPercent}%</div>
                    <div className="text-[10px] text-muted-foreground font-mono uppercase">Real ({realCount})</div>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <span className="w-3 h-3 rounded-full bg-destructive" />
                  <div>
                    <div className="text-lg font-bold">{fakePercent}%</div>
                    <div className="text-[10px] text-muted-foreground font-mono uppercase">Fake ({fakeCount})</div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Confidence Histogram */}
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
            buckets.push({ date: d.toISOString().split("T")[0], real: 0, fake: 0 })
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

        {/* Bottom: Topic Breakdown + Recent Activity */}
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

          {/* Recent Analyses */}
          <div className="card-enterprise p-6">
            <div className="flex items-center justify-between mb-5">
              <div className="flex items-center gap-2">
                <Clock className="w-4 h-4 text-accent" />
                <h3 className="text-sm font-semibold">Recent Analyses</h3>
              </div>
              <Link to="/history" className="text-[10px] text-primary hover:underline font-medium">View All →</Link>
            </div>
            <div className="space-y-2">
              {recentFive.length > 0 ? recentFive.map((r: any, i: number) => (
                <div key={i} className="flex items-center gap-3 bg-background rounded-lg px-3 py-2.5 border border-border/50">
                  <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full shrink-0 ${r.prediction === 'FAKE' ? 'bg-destructive/15 text-destructive' : 'bg-[#4ADE80]/15 text-[#4ADE80]'}`}>{r.prediction}</span>
                  <span className="text-xs text-muted-foreground truncate flex-1">{(r.text_preview || r.preview || "").slice(0, 60)}...</span>
                  <span className="text-[10px] text-muted-foreground shrink-0 font-mono">{r.confidence?.toFixed(0)}%</span>
                </div>
              )) : (
                <div className="text-center py-8">
                  <p className="text-xs text-muted-foreground">No analyses yet.</p>
                  <Link to="/analytics" className="text-xs text-primary hover:underline mt-2 inline-block">Start your first analysis →</Link>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Community Stats Banner */}
        {community && (
          <div className="mt-8 card-enterprise p-5">
            <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-widest mb-4">Community Overview</h3>
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              {[
                { val: community.total_analyses?.toLocaleString() ?? "—", label: "Total Checks", icon: "🔍" },
                { val: community.fake_percentage ? `${community.fake_percentage}%` : "—", label: "Detected Fake", icon: "⚠️" },
                { val: community.avg_confidence ? `${community.avg_confidence}%` : "—", label: "Avg Confidence", icon: "📊" },
                { val: community.today_count?.toLocaleString() ?? "—", label: "Today", icon: "📅" },
              ].map((s, i) => (
                <div key={i} className="flex items-center gap-3">
                  <span className="text-lg">{s.icon}</span>
                  <div>
                    <div className="text-base font-heading font-bold">{s.val}</div>
                    <div className="text-[10px] text-muted-foreground font-mono uppercase">{s.label}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
