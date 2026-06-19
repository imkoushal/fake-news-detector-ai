import { useState, useEffect } from "react"
import { useAuth } from "../context/AuthContext"
import { API_BASE, getAuthHeaders } from "../lib/api"
import { Loader2 } from "lucide-react"

export function AnalyticsPage() {
  const { user } = useAuth()
  const [stats, setStats] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!user) return
    Promise.all([
      fetch(`${API_BASE}/api/v1/community-stats`).then(r => r.ok ? r.json() : null),
      fetch(`${API_BASE}/api/v1/history`, { headers: getAuthHeaders() }).then(r => r.ok ? r.json() : null),
    ]).then(([community, history]) => {
      setStats({ community, history: history?.analyses ?? history ?? [] })
    }).catch(() => {}).finally(() => setLoading(false))
  }, [user])

  if (!user) return <div className="min-h-screen bg-background flex items-center justify-center text-foreground"><p>Please sign in.</p></div>
  if (loading) return <div className="min-h-screen bg-background flex items-center justify-center"><Loader2 className="w-6 h-6 animate-spin text-primary" /></div>

  const history = stats?.history || []
  const totalAnalyzed = stats?.community?.total_analyses ?? history.length
  const fakeCount = history.filter((h: any) => h.prediction === "FAKE").length
  const avgConf = history.length > 0 ? (history.reduce((s: number, h: any) => s + (h.confidence || 0), 0) / history.length).toFixed(1) : "0"

  // Simple distribution
  const realCount = history.filter((h: any) => h.prediction === "REAL").length
  const total = realCount + fakeCount || 1

  return (
    <div className="min-h-screen bg-background pt-24 px-4 md:px-12 lg:px-20 text-foreground pb-20">
      <div className="max-w-5xl mx-auto">
        <h1 className="text-3xl font-bold tracking-tight mb-2">Analytics Overview</h1>
        <p className="text-muted-foreground text-sm mb-8">System status and forensic metrics for the current verification cycle.</p>

        {/* Stat cards */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
          {[
            { label: "TOTAL ANALYZED", value: totalAnalyzed, dot: "bg-[#4ADE80]" },
            { label: "AVG CONFIDENCE", value: `${avgConf}%`, dot: "bg-[#38bdf8]" },
            { label: "FAKE DETECTED", value: fakeCount, dot: "bg-destructive" },
          ].map((s, i) => (
            <div key={i} className="bg-secondary border border-border rounded-xl p-5">
              <div className="flex items-center gap-2 mb-2">
                <span className={`w-2 h-2 rounded-full ${s.dot}`} />
                <span className="text-[10px] text-muted-foreground uppercase tracking-wider">{s.label}</span>
              </div>
              <div className="text-2xl font-bold">{s.value}</div>
            </div>
          ))}
        </div>

        {/* Distribution bar */}
        <div className="bg-secondary border border-border rounded-xl p-5 mb-8">
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
                {history.slice(0, 20).map((h: any, i: number) => (
                  <tr key={i} className="border-b border-border/50 hover:bg-background/30">
                    <td className="p-3 text-xs text-muted-foreground">{h.timestamp?.split("T")[0] ?? "—"}</td>
                    <td className="p-3"><span className={`text-xs font-medium px-2 py-0.5 rounded-full ${h.prediction === "FAKE" ? "bg-destructive/15 text-destructive" : "bg-[#4ADE80]/15 text-[#4ADE80]"}`}>{h.prediction}</span></td>
                    <td className="p-3 text-xs">{h.confidence?.toFixed(1) ?? 0}%</td>
                    <td className="p-3 text-xs max-w-[250px] truncate text-muted-foreground">{h.text_preview ?? h.preview ?? "—"}</td>
                  </tr>
                ))}
                {history.length === 0 && <tr><td colSpan={4} className="p-6 text-center text-xs text-muted-foreground">No analyses yet. Start analyzing to see data here.</td></tr>}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  )
}
