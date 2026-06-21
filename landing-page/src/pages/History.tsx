import { useState, useEffect, useMemo } from "react"
import { useAuth } from "../context/AuthContext"
import { API_BASE, getAuthHeaders } from "../lib/api"
import { Loader2, Search, Download, ArrowUpDown } from "lucide-react"
import { Button } from "../components/ui/button"

type SortKey = "date" | "confidence" | "red_flags"

export function HistoryPage() {
  const { user } = useAuth()
  const [history, setHistory] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState<"ALL" | "REAL" | "FAKE">("ALL")
  const [search, setSearch] = useState("")
  const [page, setPage] = useState(0)
  const [perPage, setPerPage] = useState(25)
  const [sortKey, setSortKey] = useState<SortKey>("date")
  const [sortAsc, setSortAsc] = useState(false)
  const [dateFrom, setDateFrom] = useState("")
  const [dateTo, setDateTo] = useState("")

  useEffect(() => {
    if (!user) return
    fetch(`${API_BASE}/api/v1/history`, { headers: getAuthHeaders() })
      .then(r => r.ok ? r.json() : null)
      .then(d => setHistory(d?.analyses ?? d ?? []))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [user])

  if (!user) return <div className="min-h-screen bg-background flex items-center justify-center text-foreground"><p>Please sign in.</p></div>
  if (loading) return <div className="min-h-screen bg-background flex items-center justify-center"><Loader2 className="w-6 h-6 animate-spin text-primary" /></div>

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) setSortAsc(!sortAsc)
    else { setSortKey(key); setSortAsc(false) }
    setPage(0)
  }

  const filtered = useMemo(() => {
    let data = history
      .filter(h => filter === "ALL" || h.prediction === filter)
      .filter(h => !search || (h.text_preview || h.preview || "").toLowerCase().includes(search.toLowerCase()))
    if (dateFrom) data = data.filter(h => h.timestamp && h.timestamp.split("T")[0] >= dateFrom)
    if (dateTo) data = data.filter(h => h.timestamp && h.timestamp.split("T")[0] <= dateTo)
    // sort
    data = [...data].sort((a, b) => {
      let cmp = 0
      if (sortKey === "date") cmp = (a.timestamp || "").localeCompare(b.timestamp || "")
      else if (sortKey === "confidence") cmp = (a.confidence || 0) - (b.confidence || 0)
      else cmp = (a.red_flag_score || 0) - (b.red_flag_score || 0)
      return sortAsc ? cmp : -cmp
    })
    return data
  }, [history, filter, search, dateFrom, dateTo, sortKey, sortAsc])

  const pages = Math.ceil(filtered.length / perPage)
  const pageData = filtered.slice(page * perPage, (page + 1) * perPage)

  const exportCsv = () => {
    const header = "Date,Prediction,Confidence,RedFlags,Preview\n"
    const rows = filtered.map(h => `${h.timestamp?.split("T")[0] ?? ""},${h.prediction},${h.confidence?.toFixed(1) ?? 0},${h.red_flag_score ?? 0},"${(h.text_preview || h.preview || "").replace(/"/g, '""')}"`).join("\n")
    const blob = new Blob([header + rows], { type: "text/csv" })
    const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = "verifai-history.csv"; a.click()
  }

  const SortBtn = ({ k, children }: { k: SortKey; children: React.ReactNode }) => (
    <button onClick={() => toggleSort(k)} className="flex items-center gap-1 hover:text-foreground transition-colors">
      {children}
      <ArrowUpDown className={`w-3 h-3 ${sortKey === k ? "text-primary" : "text-muted-foreground/40"}`} />
    </button>
  )

  return (
    <div className="min-h-screen bg-background pt-24 px-4 md:px-12 lg:px-20 text-foreground pb-20">
      <div className="max-w-5xl mx-auto">
        <div className="flex justify-between items-start mb-8 flex-wrap gap-4">
          <div>
            <h1 className="text-3xl font-bold tracking-tight mb-2">History</h1>
            <p className="text-muted-foreground text-sm">{history.length} total · {filtered.length} shown</p>
          </div>
          <Button variant="outline" size="sm" onClick={exportCsv} disabled={filtered.length === 0}>
            <Download className="w-4 h-4 mr-2" /> Export CSV
          </Button>
        </div>

        {/* Filters row */}
        <div className="flex flex-wrap gap-3 mb-4 items-center">
          {(["ALL", "REAL", "FAKE"] as const).map(f => (
            <button key={f} onClick={() => { setFilter(f); setPage(0) }}
              className={`px-4 py-1.5 rounded-full text-xs font-medium transition-colors border ${filter === f
                ? f === "FAKE" ? "bg-destructive/15 border-destructive/30 text-destructive"
                  : f === "REAL" ? "bg-[#4ADE80]/15 border-[#4ADE80]/30 text-[#4ADE80]"
                  : "bg-primary/15 border-primary/30 text-primary"
                : "border-border text-muted-foreground hover:text-foreground"}`}>
              {f} {f !== "ALL" && `(${history.filter(h => h.prediction === f).length})`}
            </button>
          ))}
          <div className="flex-1 min-w-[180px] relative">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
            <input type="text" placeholder="Search..." value={search} onChange={e => { setSearch(e.target.value); setPage(0) }}
              className="w-full bg-secondary border border-border rounded-lg pl-9 pr-4 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/50" />
          </div>
        </div>

        {/* Date range row */}
        <div className="flex flex-wrap gap-3 mb-6 items-center">
          <span className="text-xs text-muted-foreground">Date range:</span>
          <input type="date" value={dateFrom} onChange={e => { setDateFrom(e.target.value); setPage(0) }}
            className="bg-secondary border border-border rounded-lg px-3 py-1.5 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-primary/50" />
          <span className="text-xs text-muted-foreground">to</span>
          <input type="date" value={dateTo} onChange={e => { setDateTo(e.target.value); setPage(0) }}
            className="bg-secondary border border-border rounded-lg px-3 py-1.5 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-primary/50" />
          {(dateFrom || dateTo) && (
            <button onClick={() => { setDateFrom(""); setDateTo(""); setPage(0) }} className="text-xs text-primary hover:underline">Clear</button>
          )}
          <div className="ml-auto flex items-center gap-2">
            <span className="text-xs text-muted-foreground">Rows:</span>
            {[25, 50, 100].map(n => (
              <button key={n} onClick={() => { setPerPage(n); setPage(0) }}
                className={`px-2 py-1 rounded text-xs border transition-colors ${perPage === n ? "bg-primary/15 border-primary/40 text-primary" : "border-border text-muted-foreground"}`}>
                {n}
              </button>
            ))}
          </div>
        </div>

        {/* Table */}
        <div className="bg-secondary border border-border rounded-xl overflow-hidden mb-6">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead><tr className="border-b border-border bg-background/50">
                <th className="text-left p-3 text-xs text-muted-foreground font-medium">
                  <SortBtn k="date">Date</SortBtn>
                </th>
                <th className="text-left p-3 text-xs text-muted-foreground font-medium">Prediction</th>
                <th className="text-left p-3 text-xs text-muted-foreground font-medium">
                  <SortBtn k="confidence">Confidence</SortBtn>
                </th>
                <th className="text-left p-3 text-xs text-muted-foreground font-medium">
                  <SortBtn k="red_flags">Red Flags</SortBtn>
                </th>
                <th className="text-left p-3 text-xs text-muted-foreground font-medium">Preview</th>
              </tr></thead>
              <tbody>
                {pageData.map((h, i) => (
                  <tr key={i} className="border-b border-border/50 hover:bg-background/30">
                    <td className="p-3 text-xs text-muted-foreground whitespace-nowrap">{h.timestamp?.split("T")[0] ?? "—"}</td>
                    <td className="p-3"><span className={`text-xs font-medium px-2 py-0.5 rounded-full ${h.prediction === "FAKE" ? "bg-destructive/15 text-destructive" : "bg-[#4ADE80]/15 text-[#4ADE80]"}`}>{h.prediction}</span></td>
                    <td className="p-3 text-xs">{h.confidence?.toFixed(1) ?? 0}%</td>
                    <td className="p-3 text-xs">{h.red_flag_score ?? 0}/10</td>
                    <td className="p-3 text-xs max-w-[250px] truncate text-muted-foreground">{h.text_preview ?? h.preview ?? "—"}</td>
                  </tr>
                ))}
                {pageData.length === 0 && <tr><td colSpan={5} className="p-6 text-center text-xs text-muted-foreground">No results found.</td></tr>}
              </tbody>
            </table>
          </div>
        </div>

        {/* Pagination */}
        {pages > 1 && (
          <div className="flex items-center justify-center gap-2">
            <Button variant="outline" size="sm" disabled={page === 0} onClick={() => setPage(p => p - 1)}>← Prev</Button>
            <span className="text-xs text-muted-foreground">Page {page + 1} of {pages}</span>
            <Button variant="outline" size="sm" disabled={page >= pages - 1} onClick={() => setPage(p => p + 1)}>Next →</Button>
          </div>
        )}
      </div>
    </div>
  )
}
