import { useState } from "react"
import { useAuth } from "../context/AuthContext"
import { API_BASE, getAuthHeaders } from "../lib/api"
import { Loader2, ArrowLeftRight } from "lucide-react"
import { Button } from "../components/ui/button"

export function ComparePage() {
  const { user } = useAuth()
  const [textA, setTextA] = useState("")
  const [textB, setTextB] = useState("")
  const [resultA, setResultA] = useState<any>(null)
  const [resultB, setResultB] = useState<any>(null)
  const [loading, setLoading] = useState(false)

  if (!user) return <div className="min-h-screen bg-background flex items-center justify-center text-foreground"><p>Please sign in.</p></div>

  const analyze = async (text: string): Promise<any> => {
    const r = await fetch(`${API_BASE}/api/v1/analyze`, {
      method: "POST", headers: getAuthHeaders(),
      body: JSON.stringify({ text, sensitivity: 0.5 })
    })
    return r.ok ? r.json() : null
  }

  const runComparison = async () => {
    if (!textA.trim() || !textB.trim()) return
    setLoading(true); setResultA(null); setResultB(null)
    const [a, b] = await Promise.all([analyze(textA), analyze(textB)])
    setResultA(a); setResultB(b); setLoading(false)
  }

  const ResultCard = ({ label, result }: { label: string; result: any }) => {
    if (!result) return null
    const isFake = result.prediction === "FAKE"
    const conf = result.confidence?.toFixed(1) ?? 0
    const r = 30, c = 2 * Math.PI * r
    return (
      <div className="bg-secondary border border-border rounded-xl p-5 space-y-4">
        <h3 className="text-xs text-muted-foreground uppercase tracking-wider">{label}</h3>
        <div className="flex items-center gap-4">
          <div className="relative w-14 h-14 shrink-0">
            <svg viewBox="0 0 70 70" className="w-full h-full -rotate-90">
              <circle cx="35" cy="35" r={r} fill="none" stroke="hsl(var(--border))" strokeWidth="5" />
              <circle cx="35" cy="35" r={r} fill="none"
                stroke={isFake ? "hsl(var(--destructive))" : "#4ADE80"}
                strokeWidth="5" strokeLinecap="round"
                strokeDasharray={`${c}`}
                strokeDashoffset={`${c * (1 - result.confidence / 100)}`}
                className="transition-all duration-700" />
            </svg>
            <span className="absolute inset-0 flex items-center justify-center text-xs font-bold">{Math.round(result.confidence)}%</span>
          </div>
          <div>
            <p className={`text-lg font-bold ${isFake ? 'text-destructive' : 'text-[#4ADE80]'}`}>{result.prediction}</p>
            <p className="text-[11px] text-muted-foreground">{result.confidence_tier} · {conf}%</p>
          </div>
        </div>
        <div className="space-y-2">
          {[
            { label: "Fake Probability", val: result.fake_probability, color: "bg-destructive" },
            { label: "Real Probability", val: result.real_probability, color: "bg-[#4ADE80]" },
          ].map((p, i) => (
            <div key={i}>
              <div className="flex justify-between text-[11px] mb-1">
                <span className="text-muted-foreground">{p.label}</span>
                <span className="font-medium">{((p.val ?? 0) * 100).toFixed(1)}%</span>
              </div>
              <div className="h-1.5 bg-background rounded-full overflow-hidden">
                <div className={`h-full ${p.color} transition-all duration-500`} style={{ width: `${(p.val ?? 0) * 100}%` }} />
              </div>
            </div>
          ))}
        </div>
        {result.red_flag_score != null && (
          <p className="text-xs text-muted-foreground">Red flags: <span className="text-foreground font-medium">{result.red_flag_score}/10</span></p>
        )}
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background pt-24 px-4 md:px-12 lg:px-20 text-foreground pb-20">
      <div className="max-w-5xl mx-auto">
        <h1 className="text-3xl font-bold tracking-tight mb-2">Compare Articles</h1>
        <p className="text-muted-foreground text-sm mb-8">Analyze two articles side by side to compare their credibility.</p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
          <div>
            <label className="text-xs text-muted-foreground uppercase tracking-wider mb-2 block">Article A</label>
            <textarea value={textA} onChange={e => setTextA(e.target.value)}
              placeholder="Paste first article..."
              className="w-full h-40 bg-secondary border border-border rounded-xl p-4 text-sm text-foreground resize-none focus:outline-none focus:ring-2 focus:ring-primary/50" />
            <p className="text-[10px] text-muted-foreground mt-1">{textA.length} characters</p>
          </div>
          <div>
            <label className="text-xs text-muted-foreground uppercase tracking-wider mb-2 block">Article B</label>
            <textarea value={textB} onChange={e => setTextB(e.target.value)}
              placeholder="Paste second article..."
              className="w-full h-40 bg-secondary border border-border rounded-xl p-4 text-sm text-foreground resize-none focus:outline-none focus:ring-2 focus:ring-primary/50" />
            <p className="text-[10px] text-muted-foreground mt-1">{textB.length} characters</p>
          </div>
        </div>

        <div className="flex justify-center mb-8">
          <Button size="lg" onClick={runComparison} disabled={loading || !textA.trim() || !textB.trim()}>
            {loading ? <span className="flex items-center gap-2"><Loader2 className="w-4 h-4 animate-spin" /> Comparing...</span>
              : <span className="flex items-center gap-2"><ArrowLeftRight className="w-4 h-4" /> Compare Both</span>}
          </Button>
        </div>

        {(resultA || resultB) && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <ResultCard label="Article A" result={resultA} />
            <ResultCard label="Article B" result={resultB} />
          </div>
        )}
      </div>
    </div>
  )
}
