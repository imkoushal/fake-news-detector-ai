import { useState, useRef, useEffect } from "react"
import { useAuth } from "../context/AuthContext"
import { API_BASE, getAuthHeaders } from "../lib/api"
import {
  FileText, Link as LinkIcon, Mic, Upload, CheckCircle2,
  AlertTriangle, ShieldAlert, FileAudio, Loader2, ThumbsUp,
  ThumbsDown, Sparkles, ExternalLink, ChevronDown, Download,
  GraduationCap, Globe, Search
} from "lucide-react"
import { Button } from "../components/ui/button"

/* ── tiny SVG ring component ── */
function Ring({ pct, color, label, detail }: { pct: number; color: string; label: string; detail: string }) {
  const r = 34, c = 2 * Math.PI * r
  return (
    <div className="flex flex-col items-center gap-2 p-4 bg-background rounded-xl border border-border">
      <svg viewBox="0 0 80 80" className="w-16 h-16">
        <circle cx="40" cy="40" r={r} fill="none" stroke="hsl(var(--border))" strokeWidth="5" />
        <circle cx="40" cy="40" r={r} fill="none" stroke={color} strokeWidth="5"
          strokeDasharray={`${c}`} strokeDashoffset={`${c - (c * pct) / 100}`}
          strokeLinecap="round" className="transition-all duration-700"
          style={{ transform: "rotate(-90deg)", transformOrigin: "center" }} />
      </svg>
      <span className="text-lg font-bold" style={{ color }}>{pct}%</span>
      <span className="text-xs font-medium text-foreground">{label}</span>
      <span className="text-[10px] text-muted-foreground text-center leading-tight">{detail}</span>
    </div>
  )
}

export function Dashboard() {
  const { user, logout, token } = useAuth()

  const [activeTab, setActiveTab] = useState<"text" | "url" | "audio">("text")
  const [inputText, setInputText] = useState("")
  const [inputUrl, setInputUrl] = useState("")
  const [sensitivity, setSensitivity] = useState(50)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")
  const [result, setResult] = useState<any>(null)

  // secondary API results
  const [aiResult, setAiResult] = useState<any>(null)
  const [gnewsResult, setGnewsResult] = useState<any>(null)
  const [factResult, setFactResult] = useState<any>(null)
  const [feedbackSent, setFeedbackSent] = useState(false)
  const [communityStats, setCommunityStats] = useState<any>(null)
  const [showExplain, setShowExplain] = useState(false)
  const [showEducator, setShowEducator] = useState(false)

  const fileInputRef = useRef<HTMLInputElement>(null)

  // load community stats once
  useEffect(() => {
    fetch(`${API_BASE}/api/v1/community-stats`)
      .then(r => r.ok ? r.json() : null)
      .then(d => d && setCommunityStats(d))
      .catch(() => {})
  }, [])

  if (!user) return (
    <div className="min-h-screen bg-background flex items-center justify-center text-foreground">
      <Loader2 className="w-6 h-6 animate-spin mr-3" /> Checking session...
    </div>
  )

  /* ─── analysis helpers ─── */
  const analyzeData = async (text: string) => {
    setError(""); setLoading(true); setResult(null)
    setAiResult(null); setGnewsResult(null); setFactResult(null); setFeedbackSent(false)
    try {
      const res = await fetch(`${API_BASE}/api/v1/analyze`, {
        method: "POST", headers: getAuthHeaders(),
        body: JSON.stringify({ text, sensitivity: sensitivity / 100 })
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || "Analysis failed")
      setResult(data)
      // fire secondary APIs in parallel (non-blocking)
      runSecondary(text)
    } catch (err: any) { setError(err.message) }
    finally { setLoading(false) }
  }

  const runSecondary = (text: string) => {
    const h = getAuthHeaders()
    // AI verification (Groq/Gemini)
    fetch(`${API_BASE}/api/v1/smart-verify`, { method: "POST", headers: h, body: JSON.stringify({ text }) })
      .then(r => r.ok ? r.json() : null).then(d => d && setAiResult(d)).catch(() => {})
    // GNews cross-reference
    fetch(`${API_BASE}/api/v1/gnews-search`, { method: "POST", headers: h, body: JSON.stringify({ text: text.slice(0, 200) }) })
      .then(r => r.ok ? r.json() : null).then(d => d && setGnewsResult(d)).catch(() => {})
    // Fact check
    fetch(`${API_BASE}/api/v1/fact-check`, { method: "POST", headers: h, body: JSON.stringify({ text: text.slice(0, 200) }) })
      .then(r => r.ok ? r.json() : null).then(d => d && setFactResult(d)).catch(() => {})
  }

  const handleAnalyzeText = async () => {
    if (!inputText.trim()) { setError("Please enter some text."); return }
    await analyzeData(inputText)
  }

  const handleAnalyzeUrl = async () => {
    if (!inputUrl.trim()) { setError("Please enter a URL."); return }
    setError(""); setLoading(true); setResult(null)
    try {
      const r = await fetch(`${API_BASE}/api/v1/fetch-url`, {
        method: "POST", headers: getAuthHeaders(), body: JSON.stringify({ url: inputUrl })
      })
      const d = await r.json()
      if (!r.ok) throw new Error(d.detail || "Failed to fetch URL")
      if (!d.text || d.text.trim().length < 10) throw new Error("Not enough text extracted. Paste the article directly.")
      setInputText(d.text)
      await analyzeData(d.text)
    } catch (err: any) { setError(err.message); setLoading(false) }
  }

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    if (file.size > 25 * 1024 * 1024) { setError("File too large. Max 25MB."); return }
    setError(""); setLoading(true); setResult(null)
    const fd = new FormData(); fd.append("file", file)
    try {
      const r = await fetch(`${API_BASE}/api/v1/transcribe`, {
        method: "POST", headers: token ? { Authorization: `Bearer ${token}` } : {}, body: fd
      })
      const d = await r.json()
      if (!r.ok) throw new Error(d.detail || "Transcription failed")
      if (!d.text) throw new Error("No speech detected.")
      setInputText(d.text); setActiveTab("text")
      await analyzeData(d.text)
    } catch (err: any) { setError(err.message); setLoading(false) }
    if (fileInputRef.current) fileInputRef.current.value = ""
  }

  const sendFeedback = async (correct: boolean) => {
    if (!result) return
    try {
      await fetch(`${API_BASE}/api/v1/feedback`, {
        method: "POST", headers: getAuthHeaders(),
        body: JSON.stringify({
          text_preview: inputText.slice(0, 200),
          original_prediction: result.prediction,
          user_correction: correct ? result.prediction : (result.prediction === "FAKE" ? "REAL" : "FAKE")
        })
      })
      setFeedbackSent(true)
    } catch {}
  }

  const exportText = () => {
    if (!result) return
    const lines = [
      `VERIFAI — Verification Report`, `Generated: ${new Date().toISOString()}`, ``,
      `Verdict: ${result.prediction}`, `Confidence: ${result.confidence.toFixed(1)}%`,
      `Tier: ${result.confidence_tier}`, `Red Flag Score: ${result.red_flag_score}/10`,
      `Fake Probability: ${(result.fake_probability*100).toFixed(1)}%`,
      `Real Probability: ${(result.real_probability*100).toFixed(1)}%`, ``,
      `--- Input Text ---`, inputText.slice(0,2000), ``,
      aiResult ? `--- AI Analysis ---\n${aiResult.analysis||'N/A'}` : '',
      gnewsResult?.articles?.length ? `--- Web Sources ---\n${gnewsResult.articles.map((a:any)=>`• ${a.title} (${a.source?.name})`).join('\n')}` : '',
      factResult?.claims?.length ? `--- Fact Checks ---\n${factResult.claims.map((c:any)=>`• ${c.text} — ${c.claimReview?.[0]?.textualRating||'Unrated'}`).join('\n')}` : '',
    ].filter(Boolean).join('\n')
    const blob = new Blob([lines], {type:'text/plain'})
    const a = document.createElement('a'); a.href=URL.createObjectURL(blob); a.download='verifai-report.txt'; a.click()
  }

  /* ─── ring data helpers ─── */
  const mlPct = result ? Math.round(result.confidence) : 0
  const aiPct = aiResult?.confidence ?? 0
  const gnewsPct = gnewsResult?.articles?.length > 0 ? Math.min(90, gnewsResult.articles.length * 15) : 0
  const factPct = factResult?.claims?.length > 0 ? 85 : (factResult ? 40 : 0)

  return (
    <div className="min-h-screen bg-background pt-24 px-4 md:px-12 lg:px-20 text-foreground pb-20">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-3xl font-bold tracking-tight mb-1">Dashboard</h1>
            <p className="text-muted-foreground text-sm">Welcome back, {user.name}</p>
          </div>
          <Button variant="outline" size="sm" onClick={logout}>Sign Out</Button>
        </div>

        {/* ── Feature 1: Community Stats Bar ── */}
        {communityStats && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-8 animate-fade-in">
            {[
              { val: communityStats.total_analyses?.toLocaleString() ?? "—", label: "Total Checks" },
              { val: communityStats.fake_percentage ? `${communityStats.fake_percentage}%` : "—", label: "Detected Fake", cls: "text-destructive" },
              { val: communityStats.avg_confidence ? `${communityStats.avg_confidence}%` : "—", label: "Avg Confidence" },
              { val: communityStats.today_count?.toLocaleString() ?? "—", label: "Today", cls: "text-primary" },
            ].map((s, i) => (
              <div key={i} className="bg-secondary border border-border rounded-lg p-3 text-center">
                <div className={`text-lg font-bold ${s.cls || "text-foreground"}`}>{s.val}</div>
                <div className="text-[10px] text-muted-foreground uppercase tracking-wider">{s.label}</div>
              </div>
            ))}
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          {/* ── Left: Input Panel ── */}
          <div className="lg:col-span-7 flex flex-col gap-6">
            <div className="bg-secondary rounded-xl border border-border overflow-hidden shadow-sm">
              {/* Tabs */}
              <div className="flex border-b border-border bg-background/50">
                {([["text", FileText, "Text"], ["url", LinkIcon, "URL"], ["audio", Mic, "Audio"]] as const).map(([key, Icon, label]) => (
                  <button key={key} onClick={() => setActiveTab(key as any)}
                    className={`flex-1 py-3 text-sm font-medium flex items-center justify-center gap-2 transition-colors ${activeTab === key ? 'bg-secondary text-primary border-b-2 border-primary' : 'text-muted-foreground hover:text-foreground'}`}>
                    <Icon className="w-4 h-4" /> {label}
                  </button>
                ))}
              </div>

              <div className="p-6">
                {/* Text tab */}
                {activeTab === "text" && (
                  <div className="animate-fade-in">
                    <textarea placeholder="Paste the news article or social media post here..."
                      className="w-full h-48 bg-background border border-border rounded-lg p-4 text-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 resize-none"
                      value={inputText} onChange={e => setInputText(e.target.value)} maxLength={5000} />

                    {/* Feature 2: Char count + Sensitivity */}
                    <div className="flex items-center justify-between mt-2 mb-4 gap-4">
                      <span className="text-xs text-muted-foreground">{inputText.length} / 5,000 chars</span>
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-muted-foreground">Sensitivity:</span>
                        <input type="range" min={0} max={100} value={sensitivity}
                          onChange={e => setSensitivity(+e.target.value)}
                          className="w-20 h-1 accent-primary cursor-pointer" />
                        <span className="text-xs font-medium text-primary w-8">{(sensitivity / 100).toFixed(2)}</span>
                      </div>
                    </div>

                    <Button className="w-full" size="lg" onClick={handleAnalyzeText} disabled={loading}>
                      {loading ? <span className="flex items-center gap-2"><Loader2 className="w-4 h-4 animate-spin" /> Analyzing...</span> : "Analyze Content"}
                    </Button>
                  </div>
                )}

                {/* URL tab */}
                {activeTab === "url" && (
                  <div className="animate-fade-in space-y-4">
                    <input type="url" placeholder="https://example.com/news-article"
                      className="w-full bg-background border border-border rounded-lg px-4 py-3 text-foreground focus:outline-none focus:ring-2 focus:ring-primary/50"
                      value={inputUrl} onChange={e => setInputUrl(e.target.value)} />
                    <Button className="w-full" size="lg" onClick={handleAnalyzeUrl} disabled={loading}>
                      {loading ? <span className="flex items-center gap-2"><Loader2 className="w-4 h-4 animate-spin" /> Fetching & Analyzing...</span> : "Analyze URL"}
                    </Button>
                  </div>
                )}

                {/* Audio tab */}
                {activeTab === "audio" && (
                  <div className="animate-fade-in text-center py-8">
                    <div className="w-16 h-16 bg-primary/10 rounded-full flex items-center justify-center mx-auto mb-4 text-primary">
                      <FileAudio className="w-8 h-8" />
                    </div>
                    <h3 className="text-lg font-medium mb-2">Upload Audio Note</h3>
                    <p className="text-sm text-muted-foreground mb-6 max-w-sm mx-auto">
                      Upload a WhatsApp voice note or audio file. Our AI will transcribe and analyze it.
                    </p>
                    <input type="file" accept="audio/*" className="hidden" ref={fileInputRef} onChange={handleFileUpload} />
                    <Button variant="outline" size="lg" onClick={() => fileInputRef.current?.click()} disabled={loading}>
                      {loading
                        ? <span className="flex items-center gap-2"><Loader2 className="w-4 h-4 animate-spin" /> Processing...</span>
                        : <span className="flex items-center gap-2"><Upload className="w-4 h-4" /> Select Audio File</span>}
                    </Button>
                  </div>
                )}

                {error && (
                  <div className="mt-4 p-3 bg-destructive/10 border border-destructive/30 text-destructive text-sm rounded-lg flex items-start gap-2">
                    <AlertTriangle className="w-5 h-5 shrink-0 mt-0.5" /><p>{error}</p>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* ── Right: Results Panel ── */}
          <div className="lg:col-span-5 flex flex-col gap-6">
            {result ? (
              <>
                {/* Verdict card */}
                <div className="bg-secondary rounded-xl border border-border p-6 shadow-sm animate-fade-up">
                  <div className="flex items-center gap-3 mb-6">
                    {result.prediction === "FAKE"
                      ? <ShieldAlert className="w-8 h-8 text-destructive" />
                      : <CheckCircle2 className="w-8 h-8 text-[#4ADE80]" />}
                    <div>
                      <h2 className="text-xl font-bold uppercase tracking-wide">{result.prediction}</h2>
                      <p className="text-xs text-muted-foreground">{result.confidence_tier} · {result.confidence.toFixed(1)}%</p>
                    </div>
                  </div>

                  {/* Probability bars */}
                  <div className="space-y-4">
                    {[
                      { label: "Fake Probability", val: result.fake_probability, color: "bg-destructive" },
                      { label: "Real Probability", val: result.real_probability, color: "bg-[#4ADE80]" },
                      { label: "Red Flag Severity", val: result.red_flag_score / 10, color: "bg-accent", fmt: `${result.red_flag_score}/10` },
                    ].map((b, i) => (
                      <div key={i}>
                        <div className="flex justify-between text-sm mb-1">
                          <span className="text-muted-foreground">{b.label}</span>
                          <span className="font-medium">{b.fmt ?? `${(b.val * 100).toFixed(1)}%`}</span>
                        </div>
                        <div className="h-2 w-full bg-background rounded-full overflow-hidden">
                          <div className={`h-full ${b.color} transition-all duration-500`} style={{ width: `${(b.fmt ? b.val : b.val) * 100}%` }} />
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Indicator words */}
                  {(result.fake_indicator_words?.length > 0 || result.real_indicator_words?.length > 0) && (
                    <div className="mt-5 pt-4 border-t border-border">
                      <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">Key Indicator Words</h4>
                      <div className="flex flex-wrap gap-1.5">
                        {result.fake_indicator_words?.slice(0, 5).map((w: string, i: number) => (
                          <span key={`f${i}`} className="text-xs bg-destructive/15 text-destructive px-2 py-0.5 rounded-full">{w}</span>
                        ))}
                        {result.real_indicator_words?.slice(0, 5).map((w: string, i: number) => (
                          <span key={`r${i}`} className="text-xs bg-[#4ADE80]/15 text-[#4ADE80] px-2 py-0.5 rounded-full">{w}</span>
                        ))}
                      </div>
                    </div>
                  )}

                  {result.input_quality !== "sufficient" && (
                    <div className="mt-4 p-3 bg-accent/10 border border-accent/30 rounded-lg">
                      <p className="text-xs text-accent font-medium">
                        ⚠️ {result.input_quality === "short_claim" ? "Very short input — confidence capped at 60%." : "Short headline — confidence capped at 80%."} Paste the full article for best results.
                      </p>
                    </div>
                  )}

                  <div className="mt-3 text-[11px] text-muted-foreground/50">Model v{result.model_version} · {result.timestamp?.split("T")[0]}</div>
                </div>

                {/* Feature 3: 4-source verification rings */}
                <div className="grid grid-cols-2 gap-3 animate-fade-up" style={{ animationDelay: "0.15s" }}>
                  <Ring pct={mlPct} color="hsl(var(--primary))" label="ML Model" detail="5-model ensemble" />
                  <Ring pct={aiPct} color="#a78bfa" label="AI Analysis" detail={aiResult ? (aiResult.verdict || "Done") : "Loading..."} />
                  <Ring pct={gnewsPct} color="#38bdf8" label="GNews" detail={gnewsResult ? `${gnewsResult.articles?.length ?? 0} sources` : "Searching..."} />
                  <Ring pct={factPct} color="#facc15" label="Fact Check" detail={factResult ? `${factResult.claims?.length ?? 0} claims found` : "Checking..."} />
                </div>

                {/* Feature 4: AI Analysis panel */}
                {aiResult && (
                  <div className="bg-secondary rounded-xl border border-border p-5 animate-fade-up" style={{ animationDelay: "0.25s" }}>
                    <div className="flex items-center gap-2 mb-3">
                      <Sparkles className="w-4 h-4 text-[#a78bfa]" />
                      <h3 className="text-sm font-semibold">AI Verification</h3>
                      <span className={`ml-auto text-xs px-2 py-0.5 rounded-full font-medium ${
                        aiResult.verdict === "LIKELY_TRUE" ? "bg-[#4ADE80]/15 text-[#4ADE80]" :
                        aiResult.verdict === "LIKELY_FALSE" ? "bg-destructive/15 text-destructive" :
                        "bg-accent/15 text-accent"
                      }`}>{aiResult.verdict?.replace(/_/g, " ") || aiResult.credibility}</span>
                    </div>
                    <p className="text-sm text-muted-foreground leading-relaxed">{aiResult.analysis || "No detailed analysis available."}</p>
                  </div>
                )}

                {/* Feature 5: User feedback */}
                <div className="bg-secondary rounded-xl border border-border p-5 animate-fade-up" style={{ animationDelay: "0.3s" }}>
                  <h3 className="text-sm font-semibold mb-2">Was this prediction correct?</h3>
                  {feedbackSent ? (
                    <p className="text-xs text-[#4ADE80]">✓ Thank you for your feedback!</p>
                  ) : (
                    <div className="flex gap-3">
                      <Button variant="outline" size="sm" onClick={() => sendFeedback(true)}>
                        <ThumbsUp className="w-4 h-4 mr-1.5" /> Yes, correct
                      </Button>
                      <Button variant="outline" size="sm" onClick={() => sendFeedback(false)}>
                        <ThumbsDown className="w-4 h-4 mr-1.5" /> No, wrong
                      </Button>
                    </div>
                  )}
                </div>

                {/* Feature 6: Explainable AI Insights */}
                <div className="bg-secondary rounded-xl border border-border overflow-hidden animate-fade-up" style={{ animationDelay: "0.35s" }}>
                  <button onClick={() => setShowExplain(!showExplain)} className="w-full flex items-center justify-between p-5 text-left hover:bg-background/30 transition-colors">
                    <span className="text-sm font-semibold flex items-center gap-2"><Search className="w-4 h-4 text-primary" /> Explainable AI Insights</span>
                    <ChevronDown className={`w-4 h-4 text-muted-foreground transition-transform ${showExplain ? 'rotate-180' : ''}`} />
                  </button>
                  {showExplain && (
                    <div className="px-5 pb-5 space-y-3 border-t border-border pt-4">
                      {result.red_flags?.length > 0 && (
                        <div>
                          <h4 className="text-xs font-semibold text-muted-foreground uppercase mb-2">Suspicious Patterns</h4>
                          <div className="space-y-1.5">
                            {result.red_flags.map((f: any, i: number) => (
                              <div key={i} className="flex items-start gap-2 text-xs">
                                <span className="text-destructive mt-0.5">🚩</span>
                                <span className="text-muted-foreground">{typeof f === 'string' ? f : f.description || f.flag}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                      <div>
                        <h4 className="text-xs font-semibold text-muted-foreground uppercase mb-2">Model Confidence</h4>
                        <div className="grid grid-cols-2 gap-2">
                          <div className="bg-background rounded-lg p-2.5 text-center">
                            <div className="text-lg font-bold text-foreground">{(result.real_probability*100).toFixed(0)}%</div>
                            <div className="text-[10px] text-[#4ADE80]">Real Score</div>
                          </div>
                          <div className="bg-background rounded-lg p-2.5 text-center">
                            <div className="text-lg font-bold text-foreground">{(result.fake_probability*100).toFixed(0)}%</div>
                            <div className="text-[10px] text-destructive">Fake Score</div>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
                </div>

                {/* Feature 7: Web Sources (GNews) */}
                {gnewsResult?.articles?.length > 0 && (
                  <div className="bg-secondary rounded-xl border border-border p-5 animate-fade-up" style={{ animationDelay: "0.4s" }}>
                    <div className="flex items-center gap-2 mb-3">
                      <Globe className="w-4 h-4 text-[#38bdf8]" />
                      <h3 className="text-sm font-semibold">Web Sources</h3>
                      <span className="ml-auto text-xs text-muted-foreground">{gnewsResult.articles.length} found</span>
                    </div>
                    <div className="space-y-2.5">
                      {gnewsResult.articles.slice(0, 5).map((a: any, i: number) => (
                        <a key={i} href={a.url} target="_blank" rel="noopener noreferrer" className="flex items-start gap-2 group p-2 rounded-lg hover:bg-background/50 transition-colors">
                          <ExternalLink className="w-3.5 h-3.5 text-muted-foreground mt-0.5 shrink-0 group-hover:text-primary" />
                          <div className="min-w-0">
                            <p className="text-xs font-medium text-foreground group-hover:text-primary truncate">{a.title}</p>
                            <p className="text-[10px] text-muted-foreground">{a.source?.name} · {a.publishedAt?.split('T')[0]}</p>
                          </div>
                        </a>
                      ))}
                    </div>
                  </div>
                )}

                {/* Feature 8: Fact Check Database */}
                {factResult && (
                  <div className="bg-secondary rounded-xl border border-border p-5 animate-fade-up" style={{ animationDelay: "0.45s" }}>
                    <div className="flex items-center gap-2 mb-3">
                      <Search className="w-4 h-4 text-[#facc15]" />
                      <h3 className="text-sm font-semibold">Fact Check Database</h3>
                      <span className={`ml-auto text-xs px-2 py-0.5 rounded-full font-medium ${factResult.claims?.length ? 'bg-[#facc15]/15 text-[#facc15]' : 'bg-muted text-muted-foreground'}`}>
                        {factResult.claims?.length ? `${factResult.claims.length} MATCHES` : 'NO MATCHES'}
                      </span>
                    </div>
                    <p className="text-[10px] text-muted-foreground mb-3">Cross-referenced against 200+ fact-checking organizations.</p>
                    {factResult.claims?.length > 0 ? (
                      <div className="space-y-2">
                        {factResult.claims.slice(0, 4).map((c: any, i: number) => (
                          <div key={i} className="bg-background rounded-lg p-3">
                            <p className="text-xs font-medium text-foreground mb-1">{c.text}</p>
                            <p className="text-[10px] text-muted-foreground">
                              Rating: <span className="font-medium text-[#facc15]">{c.claimReview?.[0]?.textualRating || 'Unrated'}</span>
                              {c.claimReview?.[0]?.publisher?.name && ` · ${c.claimReview[0].publisher.name}`}
                            </p>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-xs text-muted-foreground">No matching claims found in fact-check databases.</p>
                    )}
                  </div>
                )}

                {/* Feature 9: Export Report */}
                <div className="bg-secondary rounded-xl border border-border p-5 animate-fade-up" style={{ animationDelay: "0.5s" }}>
                  <h3 className="text-sm font-semibold mb-3 flex items-center gap-2"><Download className="w-4 h-4" /> Export Report</h3>
                  <div className="flex gap-3">
                    <Button variant="outline" size="sm" className="flex-1" onClick={exportText}>
                      📝 Export as Text
                    </Button>
                    <Button variant="outline" size="sm" className="flex-1" onClick={() => { window.print() }}>
                      📄 Print / PDF
                    </Button>
                  </div>
                </div>

                {/* Feature 10: Educator Mode */}
                <div className="bg-secondary rounded-xl border border-border overflow-hidden animate-fade-up" style={{ animationDelay: "0.55s" }}>
                  <div className="flex items-center justify-between p-5">
                    <span className="text-sm font-semibold flex items-center gap-2"><GraduationCap className="w-4 h-4 text-primary" /> Educator Mode</span>
                    <button onClick={() => setShowEducator(!showEducator)}
                      className={`w-10 h-5 rounded-full transition-colors ${showEducator ? 'bg-primary' : 'bg-muted'} relative`}>
                      <span className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-all ${showEducator ? 'left-5' : 'left-0.5'}`} />
                    </button>
                  </div>
                  {showEducator && (
                    <div className="px-5 pb-5 border-t border-border pt-4 space-y-3">
                      {[
                        { step: 1, title: 'Text Preprocessing', desc: 'Input cleaned, normalized, and tokenized. HTML tags, special characters removed.' },
                        { step: 2, title: 'TF-IDF Vectorization', desc: `Text converted to ${result.model_version ? '25,020' : 'N'} numerical features using term frequency-inverse document frequency.` },
                        { step: 3, title: 'Meta-Feature Extraction', desc: '20 handcrafted features: readability, sentiment, entity density, sentence structure.' },
                        { step: 4, title: 'ML Ensemble Voting', desc: '5 models (LR, RF, SGD, SVC, LightGBM) independently classify and vote.' },
                        { step: 5, title: 'Red Flag Scan', desc: `Heuristic scanner detected ${result.red_flag_score}/10 severity across ${result.red_flags?.length || 0} patterns.` },
                        { step: 6, title: 'Final Verdict', desc: `Combined score: ${result.confidence.toFixed(1)}% confidence → ${result.prediction}.` },
                      ].map(s => (
                        <div key={s.step} className="flex gap-3">
                          <div className="w-6 h-6 rounded-full bg-primary/20 text-primary text-xs font-bold flex items-center justify-center shrink-0">{s.step}</div>
                          <div>
                            <p className="text-xs font-semibold text-foreground">{s.title}</p>
                            <p className="text-[11px] text-muted-foreground leading-relaxed">{s.desc}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </>
            ) : (
              <div className="bg-background border border-border border-dashed rounded-xl p-8 flex flex-col items-center justify-center text-center h-full min-h-[300px]">
                <ShieldAlert className="w-12 h-12 text-muted mb-4" />
                <h3 className="text-foreground font-medium mb-1">No Analysis Yet</h3>
                <p className="text-muted-foreground text-sm max-w-[200px]">
                  Submit text, a URL, or an audio file to see the AI verification results here.
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
