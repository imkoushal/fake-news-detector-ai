import { useState, useEffect } from "react"
import { API_BASE, getAuthHeaders } from "../lib/api"
import {
  Activity, AlertTriangle, CheckCircle, XCircle, TrendingUp,
  BarChart3, Shield, Zap, RefreshCw, Clock
} from "lucide-react"

interface HealthReport {
  status: string
  period_days: number
  total_predictions: number
  metrics?: {
    avg_confidence: number
    min_confidence: number
    max_confidence: number
    fake_rate: number
    real_rate: number
    ood_rate: number
    avg_ood_score: number
    avg_red_flag_score: number
    fake_count: number
    real_count: number
    ood_count: number
  }
  confidence_distribution?: {
    low_0_50: number
    medium_50_70: number
    high_70_90: number
    very_high_90_100: number
  }
  daily_trend?: Array<{
    date: string
    total: number
    fake: number
    real: number
    avg_confidence: number
    avg_ood: number
    ood_count: number
  }>
  alerts?: Array<{
    severity: string
    type: string
    message: string
    metric: number | null
    threshold: number | null
  }>
  model?: {
    version: string
    loaded: boolean
    config?: Record<string, unknown>
  }
  message?: string
}

function StatusBadge({ status }: { status: string }) {
  const config: Record<string, { bg: string; text: string; icon: React.ReactNode }> = {
    HEALTHY: { bg: "bg-emerald-500/15", text: "text-emerald-400", icon: <CheckCircle className="w-4 h-4" /> },
    WARNING: { bg: "bg-amber-500/15", text: "text-amber-400", icon: <AlertTriangle className="w-4 h-4" /> },
    CRITICAL: { bg: "bg-red-500/15", text: "text-red-400", icon: <XCircle className="w-4 h-4" /> },
    NO_DATA: { bg: "bg-zinc-500/15", text: "text-zinc-400", icon: <Clock className="w-4 h-4" /> },
    ERROR: { bg: "bg-red-500/15", text: "text-red-400", icon: <XCircle className="w-4 h-4" /> },
  }
  const c = config[status] || config.ERROR
  return (
    <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold ${c.bg} ${c.text}`}>
      {c.icon} {status}
    </span>
  )
}

function MetricCard({ label, value, sub, icon, color = "text-primary" }: {
  label: string; value: string; sub?: string; icon: React.ReactNode; color?: string
}) {
  return (
    <div className="bg-secondary/50 border border-border rounded-xl p-4 hover:border-primary/30 transition-colors">
      <div className="flex items-center gap-2 mb-2">
        <div className={color}>{icon}</div>
        <span className="text-xs text-muted-foreground font-medium">{label}</span>
      </div>
      <p className="text-2xl font-bold text-foreground">{value}</p>
      {sub && <p className="text-xs text-muted-foreground mt-1">{sub}</p>}
    </div>
  )
}

function ConfidenceBar({ label, value, total, color }: {
  label: string; value: number; total: number; color: string
}) {
  const pct = total > 0 ? (value / total) * 100 : 0
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs">
        <span className="text-muted-foreground">{label}</span>
        <span className="text-foreground font-mono">{value} <span className="text-muted-foreground">({pct.toFixed(1)}%)</span></span>
      </div>
      <div className="h-2 bg-background rounded-full overflow-hidden">
        <div className={`h-full rounded-full transition-all duration-700 ${color}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}

function MiniChart({ data, maxVal }: { data: number[]; maxVal: number }) {
  if (!data.length) return null
  const h = 48
  const w = 200
  const step = w / Math.max(data.length - 1, 1)
  const points = data.map((v, i) => `${i * step},${h - (v / Math.max(maxVal, 1)) * h}`).join(" ")
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="w-full h-12" preserveAspectRatio="none">
      <polyline points={points} fill="none" stroke="currentColor" strokeWidth="2" className="text-primary" />
    </svg>
  )
}

export function ModelMonitorPage() {
  const [report, setReport] = useState<HealthReport | null>(null)
  const [loading, setLoading] = useState(true)
  const [days, setDays] = useState(7)
  const [refreshing, setRefreshing] = useState(false)

  const fetchReport = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/model-health?days=${days}`, { headers: getAuthHeaders() })
      const data = await res.json()
      setReport(data)
    } catch {
      setReport({ status: "ERROR", period_days: days, total_predictions: 0, message: "Failed to connect" })
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  useEffect(() => { setLoading(true); fetchReport() }, [days])

  const handleRefresh = () => { setRefreshing(true); fetchReport() }

  if (loading) {
    return (
      <div className="p-6 md:p-8 animate-fade-in">
        <div className="max-w-6xl mx-auto space-y-6">
          <div className="skeleton h-8 w-64" />
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {[...Array(4)].map((_, i) => <div key={i} className="skeleton h-24 rounded-xl" />)}
          </div>
          <div className="skeleton h-64 rounded-xl" />
        </div>
      </div>
    )
  }

  const m = report?.metrics
  const cd = report?.confidence_distribution
  const trend = report?.daily_trend || []
  const alerts = report?.alerts || []
  const totalConf = cd ? cd.low_0_50 + cd.medium_50_70 + cd.high_70_90 + cd.very_high_90_100 : 0

  return (
    <div className="p-6 md:p-8 animate-fade-in">
      <div className="max-w-6xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-foreground flex items-center gap-2">
              <Activity className="w-6 h-6 text-primary" />
              Model Monitor
            </h1>
            <p className="text-sm text-muted-foreground mt-1">
              ML ensemble health, drift detection, and OOD monitoring
            </p>
          </div>
          <div className="flex items-center gap-3">
            <StatusBadge status={report?.status || "ERROR"} />
            <select
              value={days}
              onChange={e => setDays(Number(e.target.value))}
              className="bg-secondary border border-border rounded-lg px-3 py-1.5 text-sm text-foreground"
            >
              <option value={1}>24 hours</option>
              <option value={7}>7 days</option>
              <option value={30}>30 days</option>
              <option value={90}>90 days</option>
            </select>
            <button onClick={handleRefresh} className="p-2 rounded-lg bg-secondary border border-border hover:border-primary/50 transition-colors" title="Refresh">
              <RefreshCw className={`w-4 h-4 text-muted-foreground ${refreshing ? "animate-spin" : ""}`} />
            </button>
          </div>
        </div>

        {/* Model info bar */}
        {report?.model && (
          <div className="flex flex-wrap gap-3 text-xs">
            <span className="px-2.5 py-1 rounded-full bg-primary/10 text-primary font-mono">v{report.model.version}</span>
            <span className={`px-2.5 py-1 rounded-full font-medium ${report.model.loaded ? "bg-emerald-500/10 text-emerald-400" : "bg-red-500/10 text-red-400"}`}>
              {report.model.loaded ? "Model Loaded" : "Model Not Loaded"}
            </span>
            {report.model.config && (
              <span className="px-2.5 py-1 rounded-full bg-secondary text-muted-foreground">
                {(report.model.config as Record<string, string>).model_version || "ensemble"}
              </span>
            )}
          </div>
        )}

        {/* No data state */}
        {report?.status === "NO_DATA" && (
          <div className="text-center py-16 space-y-3">
            <Clock className="w-12 h-12 text-muted-foreground mx-auto" />
            <p className="text-lg font-medium text-foreground">No Prediction Data</p>
            <p className="text-sm text-muted-foreground">{report.message || `No predictions in the last ${days} days.`}</p>
          </div>
        )}

        {/* Metric cards */}
        {m && (
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <MetricCard
              label="Total Predictions"
              value={report!.total_predictions.toLocaleString()}
              sub={`${days} day period`}
              icon={<BarChart3 className="w-4 h-4" />}
            />
            <MetricCard
              label="Avg Confidence"
              value={`${m.avg_confidence.toFixed(1)}%`}
              sub={`Range: ${m.min_confidence.toFixed(0)}–${m.max_confidence.toFixed(0)}%`}
              icon={<TrendingUp className="w-4 h-4" />}
              color="text-emerald-400"
            />
            <MetricCard
              label="Fake Rate"
              value={`${(m.fake_rate * 100).toFixed(1)}%`}
              sub={`${m.fake_count} fake / ${m.real_count} real`}
              icon={<Shield className="w-4 h-4" />}
              color="text-amber-400"
            />
            <MetricCard
              label="OOD Rate"
              value={`${(m.ood_rate * 100).toFixed(1)}%`}
              sub={`${m.ood_count} out-of-distribution`}
              icon={<Zap className="w-4 h-4" />}
              color={m.ood_rate > 0.3 ? "text-red-400" : "text-blue-400"}
            />
          </div>
        )}

        {/* Charts row */}
        {m && (
          <div className="grid lg:grid-cols-2 gap-6">
            {/* Confidence Distribution */}
            {cd && (
              <div className="bg-secondary/50 border border-border rounded-xl p-5">
                <h3 className="text-sm font-semibold text-foreground mb-4">Confidence Distribution</h3>
                <div className="space-y-3">
                  <ConfidenceBar label="Very High (90-100%)" value={cd.very_high_90_100} total={totalConf} color="bg-emerald-500" />
                  <ConfidenceBar label="High (70-90%)" value={cd.high_70_90} total={totalConf} color="bg-blue-500" />
                  <ConfidenceBar label="Medium (50-70%)" value={cd.medium_50_70} total={totalConf} color="bg-amber-500" />
                  <ConfidenceBar label="Low (0-50%)" value={cd.low_0_50} total={totalConf} color="bg-red-500" />
                </div>
              </div>
            )}

            {/* Daily Trend Sparkline */}
            <div className="bg-secondary/50 border border-border rounded-xl p-5">
              <h3 className="text-sm font-semibold text-foreground mb-4">Daily Predictions</h3>
              {trend.length > 0 ? (
                <>
                  <MiniChart data={trend.map(d => d.total)} maxVal={Math.max(...trend.map(d => d.total))} />
                  <div className="flex justify-between text-xs text-muted-foreground mt-2">
                    <span>{trend[0]?.date}</span>
                    <span>{trend[trend.length - 1]?.date}</span>
                  </div>
                  {/* Daily breakdown table */}
                  <div className="mt-4 max-h-40 overflow-y-auto">
                    <table className="w-full text-xs">
                      <thead className="text-muted-foreground border-b border-border">
                        <tr>
                          <th className="text-left py-1 font-medium">Date</th>
                          <th className="text-right py-1 font-medium">Total</th>
                          <th className="text-right py-1 font-medium">Fake</th>
                          <th className="text-right py-1 font-medium">Real</th>
                          <th className="text-right py-1 font-medium">Conf</th>
                        </tr>
                      </thead>
                      <tbody>
                        {[...trend].reverse().map(d => (
                          <tr key={d.date} className="border-b border-border/30 hover:bg-background/50">
                            <td className="py-1 text-foreground font-mono">{d.date.slice(5)}</td>
                            <td className="py-1 text-right text-foreground">{d.total}</td>
                            <td className="py-1 text-right text-red-400">{d.fake}</td>
                            <td className="py-1 text-right text-emerald-400">{d.real}</td>
                            <td className="py-1 text-right text-blue-400">{d.avg_confidence.toFixed(0)}%</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </>
              ) : (
                <p className="text-sm text-muted-foreground text-center py-8">No trend data available</p>
              )}
            </div>
          </div>
        )}

        {/* Alerts */}
        {alerts.length > 0 && (
          <div className="bg-secondary/50 border border-border rounded-xl p-5">
            <h3 className="text-sm font-semibold text-foreground mb-4">Alerts</h3>
            <div className="space-y-2">
              {alerts.map((alert, i) => {
                const colors: Record<string, string> = {
                  critical: "border-l-red-500 bg-red-500/5",
                  warning: "border-l-amber-500 bg-amber-500/5",
                  info: "border-l-blue-500 bg-blue-500/5",
                }
                const icons: Record<string, React.ReactNode> = {
                  critical: <XCircle className="w-4 h-4 text-red-400 shrink-0" />,
                  warning: <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />,
                  info: <CheckCircle className="w-4 h-4 text-blue-400 shrink-0" />,
                }
                return (
                  <div key={i} className={`border-l-4 rounded-r-lg p-3 ${colors[alert.severity] || colors.info}`}>
                    <div className="flex items-start gap-2">
                      {icons[alert.severity] || icons.info}
                      <div>
                        <p className="text-sm text-foreground">{alert.message}</p>
                        {alert.metric !== null && alert.threshold !== null && (
                          <p className="text-xs text-muted-foreground mt-0.5 font-mono">
                            Value: {typeof alert.metric === "number" ? alert.metric.toFixed(4) : alert.metric} | Threshold: {alert.threshold}
                          </p>
                        )}
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        )}

        {/* Extra metrics */}
        {m && (
          <div className="bg-secondary/50 border border-border rounded-xl p-5">
            <h3 className="text-sm font-semibold text-foreground mb-4">Detailed Metrics</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              {[
                { label: "Avg OOD Score", value: m.avg_ood_score.toFixed(4) },
                { label: "Avg Red Flag Score", value: m.avg_red_flag_score.toFixed(4) },
                { label: "Min Confidence", value: `${m.min_confidence.toFixed(1)}%` },
                { label: "Max Confidence", value: `${m.max_confidence.toFixed(1)}%` },
              ].map(item => (
                <div key={item.label}>
                  <p className="text-xs text-muted-foreground">{item.label}</p>
                  <p className="text-foreground font-mono font-semibold">{item.value}</p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
