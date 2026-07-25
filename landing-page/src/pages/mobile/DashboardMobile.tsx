import { Link } from "react-router-dom"
import {
  TrendingUp, TrendingDown, Activity, Target,
  Search, Clock, ShieldCheck, PieChart, BarChart3
} from "lucide-react"
import type { DashboardViewProps } from "../Dashboard"

export function DashboardMobile({
  user, greeting, totalAnalyzed, fakeCount, realCount, avgConf,
  fakePercent, realPercent, total, confBuckets,
  allHistory, filtered, range, setRange, community
}: DashboardViewProps) {

  const DonutChart = () => {
    const size = 110, cx = size / 2, cy = size / 2, r = 40, stroke = 12
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
        <text x={cx} y={cy - 4} textAnchor="middle" className="fill-foreground text-xl font-bold" fontSize="18">{totalAnalyzed}</text>
        <text x={cx} y={cy + 10} textAnchor="middle" className="fill-muted-foreground" fontSize="9">Total</text>
      </svg>
    )
  }

  const recentFive = allHistory.slice(0, 3) // fewer on mobile

  return (
    <div className="bg-background px-4 py-5 text-foreground w-full max-w-full overflow-x-hidden min-h-screen">
      <div className="w-full space-y-4">

        {/* Compact Greeting */}
        <div className="card-enterprise p-4 relative overflow-hidden">
          <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-primary via-accent to-primary" />
          <h1 className="text-lg font-heading font-extrabold tracking-tight">{greeting}, {user?.name?.split(" ")[0]}</h1>
          <p className="text-[11px] text-muted-foreground mt-0.5">Your misinformation detection overview</p>
          <div className="flex items-center gap-2 mt-2">
            <span className="stat-pill text-[10px]"><span className="w-1.5 h-1.5 rounded-full bg-[#4ADE80] animate-pulse inline-block mr-1" />Online</span>
            <span className="stat-pill font-mono text-[10px]">{new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}</span>
          </div>
        </div>

        {/* Quick Actions — horizontal scroll on mobile */}
        <div className="flex gap-3 overflow-x-auto pb-1 -mx-1 px-1 snap-x">
          <Link to="/analytics" className="card-enterprise p-4 min-w-[140px] flex-shrink-0 snap-start hover:border-primary/50 transition-all group">
            <div className="w-9 h-9 rounded-xl bg-primary/10 text-primary flex items-center justify-center mb-2 group-hover:scale-105 transition-transform"><Search className="w-4 h-4" /></div>
            <div className="text-xs font-semibold">Analyze</div>
            <div className="text-[10px] text-muted-foreground mt-0.5">Text, URL, Audio</div>
          </Link>
          <Link to="/history" className="card-enterprise p-4 min-w-[140px] flex-shrink-0 snap-start hover:border-accent/50 transition-all group">
            <div className="w-9 h-9 rounded-xl bg-accent/10 text-accent flex items-center justify-center mb-2 group-hover:scale-105 transition-transform"><Clock className="w-4 h-4" /></div>
            <div className="text-xs font-semibold">History</div>
            <div className="text-[10px] text-muted-foreground mt-0.5">{allHistory.length} saved</div>
          </Link>
          <Link to="/compare" className="card-enterprise p-4 min-w-[140px] flex-shrink-0 snap-start hover:border-[#4ADE80]/50 transition-all group">
            <div className="w-9 h-9 rounded-xl bg-[#4ADE80]/10 text-[#4ADE80] flex items-center justify-center mb-2 group-hover:scale-105 transition-transform"><ShieldCheck className="w-4 h-4" /></div>
            <div className="text-xs font-semibold">Compare</div>
            <div className="text-[10px] text-muted-foreground mt-0.5">Side by side</div>
          </Link>
        </div>

        {/* Stats — 2x2 grid, compact */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-[10px] font-semibold text-muted-foreground uppercase tracking-widest">Stats</h2>
            <div className="flex gap-1">
              {([
                [7, "7D"], [30, "30D"], [0, "All"]
              ] as [number, string][]).map(([v, label]) => (
                <button key={v} onClick={() => setRange(v as any)}
                  className={`px-2 py-0.5 rounded-md text-[10px] font-medium border transition-all ${range === v ? "bg-primary/20 border-primary/50 text-primary" : "border-border text-muted-foreground"}`}>
                  {label}
                </button>
              ))}
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            {[
              { label: "ANALYZED", value: totalAnalyzed, icon: <Activity className="w-4 h-4" />, color: "text-primary bg-primary/10" },
              { label: "FAKE", value: fakeCount, icon: <TrendingDown className="w-4 h-4" />, color: "text-destructive bg-destructive/10" },
              { label: "REAL", value: realCount, icon: <TrendingUp className="w-4 h-4" />, color: "text-[#4ADE80] bg-[#4ADE80]/10" },
              { label: "AVG CONF", value: `${avgConf.toFixed(0)}%`, icon: <Target className="w-4 h-4" />, color: "text-accent bg-accent/10" },
            ].map((s, i) => (
              <div key={i} className="card-enterprise p-3.5">
                <div className={`w-8 h-8 rounded-lg flex items-center justify-center mb-2 ${s.color}`}>{s.icon}</div>
                <div className="text-xl font-heading font-extrabold">{s.value}</div>
                <div className="text-[9px] text-muted-foreground font-mono uppercase tracking-wider mt-0.5">{s.label}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Distribution — Donut compact */}
        <div className="card-enterprise p-4">
          <div className="flex items-center gap-2 mb-3">
            <PieChart className="w-4 h-4 text-primary" />
            <h3 className="text-sm font-semibold">Distribution</h3>
          </div>
          <div className="flex items-center justify-center gap-6">
            <DonutChart />
            <div className="flex flex-col gap-3">
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 rounded-full bg-[#4ADE80] shrink-0" />
                <div>
                  <div className="text-base font-bold">{realPercent}%</div>
                  <div className="text-[9px] text-muted-foreground font-mono">REAL ({realCount})</div>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 rounded-full bg-destructive shrink-0" />
                <div>
                  <div className="text-base font-bold">{fakePercent}%</div>
                  <div className="text-[9px] text-muted-foreground font-mono">FAKE ({fakeCount})</div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Confidence — compact horizontal bars */}
        <div className="card-enterprise p-4">
          <div className="flex items-center gap-2 mb-3">
            <BarChart3 className="w-4 h-4 text-accent" />
            <h3 className="text-sm font-semibold">Confidence</h3>
          </div>
          {(() => {
            const maxCount = Math.max(...confBuckets.map(b => b.count), 1)
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
          })()}
          {filtered.length === 0 && <p className="text-[10px] text-muted-foreground text-center py-4">No data yet.</p>}
        </div>

        {/* Recent Analyses — compact list */}
        <div className="card-enterprise p-4">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Clock className="w-4 h-4 text-accent" />
              <h3 className="text-sm font-semibold">Recent</h3>
            </div>
            <Link to="/history" className="text-[10px] text-primary hover:underline font-medium">All →</Link>
          </div>
          <div className="space-y-2">
            {recentFive.length > 0 ? recentFive.map((r: any, i: number) => (
              <div key={i} className="flex items-center gap-2 bg-background rounded-lg px-2.5 py-2 border border-border/50">
                <span className={`text-[9px] font-medium px-1.5 py-0.5 rounded-full shrink-0 ${r.prediction === 'FAKE' ? 'bg-destructive/15 text-destructive' : 'bg-[#4ADE80]/15 text-[#4ADE80]'}`}>{r.prediction}</span>
                <span className="text-[11px] text-muted-foreground truncate flex-1">{(r.text_preview || r.preview || "").slice(0, 40)}...</span>
                <span className="text-[9px] text-muted-foreground shrink-0 font-mono">{r.confidence?.toFixed(0)}%</span>
              </div>
            )) : (
              <div className="text-center py-6">
                <p className="text-[11px] text-muted-foreground">No analyses yet</p>
                <Link to="/analytics" className="text-[11px] text-primary hover:underline mt-1 inline-block">Start analyzing →</Link>
              </div>
            )}
          </div>
        </div>

        {/* Community — compact */}
        {community && (
          <div className="card-enterprise p-4">
            <h3 className="text-[10px] font-semibold text-muted-foreground uppercase tracking-widest mb-3">Community</h3>
            <div className="grid grid-cols-2 gap-3">
              {[
                { val: community.total_analyses?.toLocaleString() ?? "—", label: "Checks", icon: "🔍" },
                { val: community.fake_percentage ? `${community.fake_percentage}%` : "—", label: "Fake", icon: "⚠️" },
                { val: community.avg_confidence ? `${community.avg_confidence}%` : "—", label: "Avg Conf", icon: "📊" },
                { val: community.today_count?.toLocaleString() ?? "—", label: "Today", icon: "📅" },
              ].map((s, i) => (
                <div key={i} className="flex items-center gap-2">
                  <span className="text-sm">{s.icon}</span>
                  <div>
                    <div className="text-sm font-heading font-bold">{s.val}</div>
                    <div className="text-[9px] text-muted-foreground font-mono uppercase">{s.label}</div>
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
