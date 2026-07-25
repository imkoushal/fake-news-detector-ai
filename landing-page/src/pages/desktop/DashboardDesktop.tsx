import { Link } from "react-router-dom"
import {
  TrendingUp, TrendingDown, BarChart3, PieChart, Activity, Target,
  Search, ArrowRight, Clock, ShieldCheck
} from "lucide-react"
import type { DashboardViewProps } from "../Dashboard"

export function DashboardDesktop({
  user, greeting, totalAnalyzed, fakeCount, realCount, avgConf,
  fakePercent, realPercent, total, confBuckets, topicMap,
  allHistory, filtered, range, setRange, community
}: DashboardViewProps) {

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
    <div className="bg-background p-4 sm:p-6 md:p-8 text-foreground w-full max-w-full overflow-x-hidden min-h-screen">
      <div className="w-full max-w-[1600px] mx-auto space-y-6">

        {/* Greeting Header */}
        <div className="card-enterprise p-5 sm:p-6 relative overflow-hidden">
          <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-primary via-accent to-primary" />
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h1 className="text-xl sm:text-2xl lg:text-3xl font-heading font-extrabold tracking-tight">{greeting}, {user?.name?.split(" ")[0]}</h1>
              <p className="text-xs sm:text-sm text-muted-foreground mt-1">Here's your misinformation detection overview.</p>
            </div>
            <div className="flex items-center gap-2.5 flex-wrap">
              <span className="stat-pill"><span className="w-2 h-2 rounded-full bg-[#4ADE80] animate-pulse inline-block mr-1.5" />System Online</span>
              <span className="stat-pill font-mono text-xs">{new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}</span>
            </div>
          </div>
        </div>

        {/* Quick Actions */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <Link to="/analytics" className="card-enterprise p-5 hover:border-primary/50 transition-all duration-200 group cursor-pointer hover:shadow-lg hover:shadow-primary/5">
            <div className="flex items-center gap-4">
              <div className="w-10 h-10 rounded-xl bg-primary/10 text-primary flex items-center justify-center shrink-0 group-hover:scale-105 transition-transform"><Search className="w-5 h-5" /></div>
              <div className="flex-1">
                <div className="text-sm font-semibold group-hover:text-primary transition-colors">Analyze Content</div>
                <div className="text-xs text-muted-foreground mt-0.5">Check text, URL, or audio</div>
              </div>
              <ArrowRight className="w-4 h-4 text-muted-foreground group-hover:text-primary group-hover:translate-x-0.5 transition-all shrink-0" />
            </div>
          </Link>
          <Link to="/history" className="card-enterprise p-5 hover:border-accent/50 transition-all duration-200 group cursor-pointer hover:shadow-lg hover:shadow-accent/5">
            <div className="flex items-center gap-4">
              <div className="w-10 h-10 rounded-xl bg-accent/10 text-accent flex items-center justify-center shrink-0 group-hover:scale-105 transition-transform"><Clock className="w-5 h-5" /></div>
              <div className="flex-1">
                <div className="text-sm font-semibold group-hover:text-accent transition-colors">View History</div>
                <div className="text-xs text-muted-foreground mt-0.5">{allHistory.length} analyses stored</div>
              </div>
              <ArrowRight className="w-4 h-4 text-muted-foreground group-hover:text-accent group-hover:translate-x-0.5 transition-all shrink-0" />
            </div>
          </Link>
          <Link to="/compare" className="card-enterprise p-5 hover:border-[#4ADE80]/50 transition-all duration-200 group cursor-pointer hover:shadow-lg hover:shadow-[#4ADE80]/5">
            <div className="flex items-center gap-4">
              <div className="w-10 h-10 rounded-xl bg-[#4ADE80]/10 text-[#4ADE80] flex items-center justify-center shrink-0 group-hover:scale-105 transition-transform"><ShieldCheck className="w-5 h-5" /></div>
              <div className="flex-1">
                <div className="text-sm font-semibold group-hover:text-[#4ADE80] transition-colors">Compare Articles</div>
                <div className="text-xs text-muted-foreground mt-0.5">Side-by-side verification</div>
              </div>
              <ArrowRight className="w-4 h-4 text-muted-foreground group-hover:text-[#4ADE80] group-hover:translate-x-0.5 transition-all shrink-0" />
            </div>
          </Link>
        </div>

        {/* Community + User Stat Cards */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xs font-semibold text-muted-foreground uppercase tracking-widest">Your Statistics</h2>
            <div className="flex gap-1.5">
              {([
                [7, "7D"], [30, "30D"], [90, "90D"], [0, "All"]
              ] as [number, string][]).map(([v, label]) => (
                <button key={v} onClick={() => setRange(v as any)}
                  className={`px-3 py-1 rounded-lg text-xs font-medium border transition-all ${range === v ? "bg-primary/20 border-primary/50 text-primary shadow-sm" : "border-border text-muted-foreground hover:text-foreground hover:bg-secondary/50"}`}>
                  {label}
                </button>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 stagger-children">
            {[
              { label: "ARTICLES ANALYZED", value: totalAnalyzed, icon: <Activity className="w-5 h-5" />, color: "text-primary bg-primary/10" },
              { label: "FAKE DETECTED", value: fakeCount, icon: <TrendingDown className="w-5 h-5" />, color: "text-destructive bg-destructive/10" },
              { label: "VERIFIED REAL", value: realCount, icon: <TrendingUp className="w-5 h-5" />, color: "text-[#4ADE80] bg-[#4ADE80]/10" },
              { label: "AVG CONFIDENCE", value: `${avgConf.toFixed(1)}%`, icon: <Target className="w-5 h-5" />, color: "text-accent bg-accent/10" },
            ].map((s, i) => (
              <div key={i} className="card-enterprise p-5 fade-up-stagger hover:border-border/80 transition-all">
                <div className="flex items-center justify-between mb-3">
                  <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${s.color}`}>{s.icon}</div>
                </div>
                <div className="text-2xl lg:text-3xl font-heading font-extrabold">{s.value}</div>
                <div className="text-xs text-muted-foreground font-mono uppercase tracking-wider mt-1.5">{s.label}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Charts Row */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Donut */}
          <div className="card-enterprise p-6">
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-2.5">
                <PieChart className="w-5 h-5 text-primary" />
                <h3 className="text-base font-semibold">Prediction Distribution</h3>
              </div>
            </div>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-8 py-2">
              <DonutChart />
              <div className="flex sm:flex-col gap-6 sm:gap-6 justify-center">
                <div className="flex items-center gap-3">
                  <span className="w-3.5 h-3.5 rounded-full bg-[#4ADE80] shrink-0 shadow-sm shadow-[#4ADE80]/30" />
                  <div>
                    <div className="text-xl font-bold">{realPercent}%</div>
                    <div className="text-xs text-muted-foreground font-mono uppercase tracking-wide">Real ({realCount})</div>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <span className="w-3.5 h-3.5 rounded-full bg-destructive shrink-0 shadow-sm shadow-destructive/30" />
                  <div>
                    <div className="text-xl font-bold">{fakePercent}%</div>
                    <div className="text-xs text-muted-foreground font-mono uppercase tracking-wide">Fake ({fakeCount})</div>
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
