import { Link } from "react-router-dom"
import {
  TrendingUp, TrendingDown, BarChart3, PieChart, Activity, Target,
  Search, ArrowRight, Clock, ShieldCheck
} from "lucide-react"
import type { DashboardViewProps } from "../Dashboard"

/**
 * P4-2: Unified responsive Dashboard view.
 * Replaces the separate DashboardDesktop / DashboardMobile components.
 * Uses Tailwind breakpoints (md:, lg:) for layout differences, and
 * a single `isMobile` prop only where structural DOM changes are needed
 * (e.g., omitting the Activity Trend chart on phones).
 */
export function DashboardView({
  user, greeting, totalAnalyzed, fakeCount, realCount, avgConf,
  fakePercent, realPercent, total, confBuckets, topicMap,
  allHistory, filtered, range, setRange, community, isMobile
}: DashboardViewProps & { isMobile: boolean }) {

  /* ── Donut Chart ── */
  const donutSize = isMobile ? 110 : 140
  const donutR = isMobile ? 40 : 50
  const donutStroke = isMobile ? 12 : 14
  const DonutChart = () => {
    const cx = donutSize / 2, cy = donutSize / 2
    const circumference = 2 * Math.PI * donutR
    const realArc = (realCount / total) * circumference
    const fakeArc = (fakeCount / total) * circumference
    return (
      <svg width={donutSize} height={donutSize} viewBox={`0 0 ${donutSize} ${donutSize}`}>
        <circle cx={cx} cy={cy} r={donutR} fill="none" stroke="hsl(var(--border))" strokeWidth={donutStroke} opacity="0.3" />
        <circle cx={cx} cy={cy} r={donutR} fill="none" stroke="#4ADE80" strokeWidth={donutStroke}
          strokeDasharray={`${realArc} ${circumference}`} strokeDashoffset="0"
          transform={`rotate(-90 ${cx} ${cy})`} strokeLinecap="round" className="transition-all duration-700" />
        <circle cx={cx} cy={cy} r={donutR} fill="none" stroke="hsl(var(--destructive))" strokeWidth={donutStroke}
          strokeDasharray={`${fakeArc} ${circumference}`} strokeDashoffset={`-${realArc}`}
          transform={`rotate(-90 ${cx} ${cy})`} strokeLinecap="round" className="transition-all duration-700" />
        <text x={cx} y={cy - (isMobile ? 4 : 6)} textAnchor="middle" className="fill-foreground font-bold"
          fontSize={isMobile ? 18 : 22}>{totalAnalyzed}</text>
        <text x={cx} y={cy + (isMobile ? 10 : 12)} textAnchor="middle" className="fill-muted-foreground"
          fontSize={isMobile ? 9 : 10}>Total</text>
      </svg>
    )
  }

  const recentCount = isMobile ? 3 : 5
  const recentItems = allHistory.slice(0, recentCount)

  /* ── Range filters: mobile skips 90D ── */
  const rangeOptions = isMobile
    ? ([[7, "7D"], [30, "30D"], [0, "All"]] as [number, string][])
    : ([[7, "7D"], [30, "30D"], [90, "90D"], [0, "All"]] as [number, string][])

  return (
    <div className="bg-background px-4 py-5 md:p-6 lg:p-8 text-foreground w-full max-w-full overflow-x-hidden min-h-screen">
      <div className="w-full max-w-[1600px] mx-auto space-y-4 md:space-y-6">

        {/* ── Greeting Header ── */}
        <div className="card-enterprise p-4 md:p-5 lg:p-6 relative overflow-hidden">
          <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-primary via-accent to-primary" />
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h1 className="text-lg md:text-xl lg:text-3xl font-heading font-extrabold tracking-tight">
                {greeting}, {user?.name?.split(" ")[0]}
              </h1>
              <p className="text-[11px] md:text-xs lg:text-sm text-muted-foreground mt-0.5 md:mt-1">
                {isMobile ? "Your misinformation detection overview" : "Here's your misinformation detection overview."}
              </p>
            </div>
            <div className="flex items-center gap-2 md:gap-2.5 flex-wrap">
              <span className="stat-pill text-[10px] md:text-xs">
                <span className="w-1.5 h-1.5 md:w-2 md:h-2 rounded-full bg-[#4ADE80] animate-pulse inline-block mr-1 md:mr-1.5" />
                {isMobile ? "Online" : "System Online"}
              </span>
              <span className="stat-pill font-mono text-[10px] md:text-xs">
                {new Date().toLocaleDateString('en-US', {
                  month: 'short', day: 'numeric', ...(isMobile ? {} : { year: 'numeric' })
                })}
              </span>
            </div>
          </div>
        </div>

        {/* ── Quick Actions ── */}
        <div className={isMobile
          ? "flex gap-3 overflow-x-auto pb-1 -mx-1 px-1 snap-x"
          : "grid grid-cols-1 sm:grid-cols-3 gap-4"
        }>
          {[
            { to: "/analytics", icon: Search, label: "Analyze", sub: isMobile ? "Text, URL, Audio" : "Check text, URL, or audio", color: "primary" },
            { to: "/history", icon: Clock, label: isMobile ? "History" : "View History", sub: isMobile ? `${allHistory.length} saved` : `${allHistory.length} analyses stored`, color: "accent" },
            { to: "/compare", icon: ShieldCheck, label: isMobile ? "Compare" : "Compare Articles", sub: isMobile ? "Side by side" : "Side-by-side verification", color: "[#4ADE80]" },
          ].map(({ to, icon: Icon, label, sub, color }) => (
            <Link key={to} to={to}
              className={`card-enterprise hover:border-${color}/50 transition-all duration-200 group cursor-pointer hover:shadow-lg hover:shadow-${color}/5 ${isMobile ? "p-4 min-w-[140px] flex-shrink-0 snap-start" : "p-5"}`}>
              <div className={isMobile ? "" : "flex items-center gap-4"}>
                <div className={`w-9 h-9 md:w-10 md:h-10 rounded-xl bg-${color}/10 text-${color} flex items-center justify-center ${isMobile ? "mb-2" : "shrink-0"} group-hover:scale-105 transition-transform`}>
                  <Icon className="w-4 h-4 md:w-5 md:h-5" />
                </div>
                <div className={isMobile ? "" : "flex-1"}>
                  <div className={`text-xs md:text-sm font-semibold group-hover:text-${color} transition-colors`}>{label}</div>
                  <div className="text-[10px] md:text-xs text-muted-foreground mt-0.5">{sub}</div>
                </div>
                {!isMobile && <ArrowRight className={`w-4 h-4 text-muted-foreground group-hover:text-${color} group-hover:translate-x-0.5 transition-all shrink-0`} />}
              </div>
            </Link>
          ))}
        </div>

        {/* ── Stats Grid ── */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-[10px] md:text-xs font-semibold text-muted-foreground uppercase tracking-widest">
              {isMobile ? "Stats" : "Your Statistics"}
            </h2>
            <div className="flex gap-1 md:gap-1.5">
              {rangeOptions.map(([v, label]) => (
                <button key={v} onClick={() => setRange(v as any)}
                  className={`px-2 md:px-3 py-0.5 md:py-1 rounded-md md:rounded-lg text-[10px] md:text-xs font-medium border transition-all ${range === v
                    ? "bg-primary/20 border-primary/50 text-primary shadow-sm"
                    : "border-border text-muted-foreground hover:text-foreground hover:bg-secondary/50"}`}>
                  {label}
                </button>
              ))}
            </div>
          </div>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 md:gap-4 stagger-children">
            {[
              { label: isMobile ? "ANALYZED" : "ARTICLES ANALYZED", value: totalAnalyzed, icon: <Activity className="w-4 h-4 md:w-5 md:h-5" />, color: "text-primary bg-primary/10" },
              { label: isMobile ? "FAKE" : "FAKE DETECTED", value: fakeCount, icon: <TrendingDown className="w-4 h-4 md:w-5 md:h-5" />, color: "text-destructive bg-destructive/10" },
              { label: isMobile ? "REAL" : "VERIFIED REAL", value: realCount, icon: <TrendingUp className="w-4 h-4 md:w-5 md:h-5" />, color: "text-[#4ADE80] bg-[#4ADE80]/10" },
              { label: "AVG CONF", value: `${avgConf.toFixed(isMobile ? 0 : 1)}%`, icon: <Target className="w-4 h-4 md:w-5 md:h-5" />, color: "text-accent bg-accent/10" },
            ].map((s, i) => (
              <div key={i} className="card-enterprise p-3.5 md:p-5 fade-up-stagger hover:border-border/80 transition-all">
                <div className={`w-8 h-8 md:w-10 md:h-10 rounded-lg md:rounded-xl flex items-center justify-center ${s.color} mb-2 md:mb-3`}>{s.icon}</div>
                <div className="text-xl md:text-2xl lg:text-3xl font-heading font-extrabold">{s.value}</div>
                <div className="text-[9px] md:text-xs text-muted-foreground font-mono uppercase tracking-wider mt-0.5 md:mt-1.5">{s.label}</div>
              </div>
            ))}
          </div>
        </div>

        {/* ── Charts: Donut + Confidence ── */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 md:gap-6">
          {/* Donut */}
          <div className="card-enterprise p-4 md:p-6">
            <div className="flex items-center gap-2 md:gap-2.5 mb-3 md:mb-6">
              <PieChart className="w-4 h-4 md:w-5 md:h-5 text-primary" />
              <h3 className="text-sm md:text-base font-semibold">{isMobile ? "Distribution" : "Prediction Distribution"}</h3>
            </div>
            <div className="flex items-center justify-center gap-6 md:gap-8 py-0 md:py-2">
              <DonutChart />
              <div className="flex flex-col gap-3 md:gap-6">
                <div className="flex items-center gap-2 md:gap-3">
                  <span className="w-3 h-3 md:w-3.5 md:h-3.5 rounded-full bg-[#4ADE80] shrink-0 shadow-sm shadow-[#4ADE80]/30" />
                  <div>
                    <div className="text-base md:text-xl font-bold">{realPercent}%</div>
                    <div className="text-[9px] md:text-xs text-muted-foreground font-mono uppercase tracking-wide">REAL ({realCount})</div>
                  </div>
                </div>
                <div className="flex items-center gap-2 md:gap-3">
                  <span className="w-3 h-3 md:w-3.5 md:h-3.5 rounded-full bg-destructive shrink-0 shadow-sm shadow-destructive/30" />
                  <div>
                    <div className="text-base md:text-xl font-bold">{fakePercent}%</div>
                    <div className="text-[9px] md:text-xs text-muted-foreground font-mono uppercase tracking-wide">FAKE ({fakeCount})</div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Confidence Histogram */}
          <div className="card-enterprise p-4 md:p-6">
            <div className="flex items-center gap-2 mb-3 md:mb-5">
              <BarChart3 className="w-4 h-4 text-accent" />
              <h3 className="text-sm font-semibold">{isMobile ? "Confidence" : "Confidence Distribution"}</h3>
            </div>
            {(() => {
              const maxCount = Math.max(...confBuckets.map(b => b.count), 1)
              if (isMobile) {
                // Horizontal bars for mobile
                return (
                  <div className="space-y-2">
                    {confBuckets.map((b, i) => (
                      <div key={i} className="flex items-center gap-2">
                        <span className="text-[9px] text-muted-foreground font-mono w-12 text-right shrink-0">{b.label}</span>
                        <div className="flex-1 h-4 bg-background rounded overflow-hidden">
                          <div className="h-full bg-gradient-to-r from-primary/80 to-accent/80 rounded transition-all duration-500"
                            style={{ width: `${Math.max((b.count / maxCount) * 100, 2)}%` }} />
                        </div>
                        <span className="text-[10px] text-muted-foreground font-mono w-6">{b.count}</span>
                      </div>
                    ))}
                  </div>
                )
              }
              // Vertical bars for desktop
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
            {filtered.length === 0 && <p className="text-[10px] md:text-xs text-muted-foreground text-center py-4 md:py-8">No data yet.</p>}
          </div>
        </div>

        {/* ── Activity Trend (desktop only) ── */}
        {!isMobile && (() => {
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

        {/* ── Bottom: Topic Breakdown (desktop) + Recent Analyses ── */}
        <div className={`grid grid-cols-1 ${!isMobile ? "lg:grid-cols-2" : ""} gap-4 md:gap-6`}>
          {/* Topic Breakdown — desktop only */}
          {!isMobile && (
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
          )}

          {/* Recent Analyses */}
          <div className="card-enterprise p-4 md:p-6">
            <div className="flex items-center justify-between mb-3 md:mb-5">
              <div className="flex items-center gap-2">
                <Clock className="w-4 h-4 text-accent" />
                <h3 className="text-sm font-semibold">{isMobile ? "Recent" : "Recent Analyses"}</h3>
              </div>
              <Link to="/history" className="text-[10px] text-primary hover:underline font-medium">{isMobile ? "All →" : "View All →"}</Link>
            </div>
            <div className="space-y-2">
              {recentItems.length > 0 ? recentItems.map((r: any, i: number) => (
                <div key={i} className="flex items-center gap-2 md:gap-3 bg-background rounded-lg px-2.5 md:px-3 py-2 md:py-2.5 border border-border/50">
                  <span className={`text-[9px] md:text-[10px] font-medium px-1.5 md:px-2 py-0.5 rounded-full shrink-0 ${r.prediction === 'FAKE' ? 'bg-destructive/15 text-destructive' : 'bg-[#4ADE80]/15 text-[#4ADE80]'}`}>{r.prediction}</span>
                  <span className="text-[11px] md:text-xs text-muted-foreground truncate flex-1">{(r.text_preview || r.preview || "").slice(0, isMobile ? 40 : 60)}...</span>
                  <span className="text-[9px] md:text-[10px] text-muted-foreground shrink-0 font-mono">{r.confidence?.toFixed(0)}%</span>
                </div>
              )) : (
                <div className="text-center py-6 md:py-8">
                  <p className="text-[11px] md:text-xs text-muted-foreground">{isMobile ? "No analyses yet" : "No analyses yet."}</p>
                  <Link to="/analytics" className="text-[11px] md:text-xs text-primary hover:underline mt-1 md:mt-2 inline-block">{isMobile ? "Start analyzing →" : "Start your first analysis →"}</Link>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* ── Community Stats ── */}
        {community && (
          <div className={`card-enterprise p-4 md:p-5 ${!isMobile ? "mt-8" : ""}`}>
            <h3 className="text-[10px] md:text-xs font-semibold text-muted-foreground uppercase tracking-widest mb-3 md:mb-4">{isMobile ? "Community" : "Community Overview"}</h3>
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 md:gap-4">
              {[
                { val: community.total_analyses?.toLocaleString() ?? "—", label: isMobile ? "Checks" : "Total Checks", icon: "🔍" },
                { val: community.fake_percentage ? `${community.fake_percentage}%` : "—", label: isMobile ? "Fake" : "Detected Fake", icon: "⚠️" },
                { val: community.avg_confidence ? `${community.avg_confidence}%` : "—", label: "Avg Conf", icon: "📊" },
                { val: community.today_count?.toLocaleString() ?? "—", label: "Today", icon: "📅" },
              ].map((s, i) => (
                <div key={i} className="flex items-center gap-2 md:gap-3">
                  <span className="text-sm md:text-lg">{s.icon}</span>
                  <div>
                    <div className="text-sm md:text-base font-heading font-bold">{s.val}</div>
                    <div className="text-[9px] md:text-[10px] text-muted-foreground font-mono uppercase">{s.label}</div>
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
