import { useState, useRef, useEffect, useCallback } from "react"
import { useAuth } from "../context/AuthContext"
import { API_BASE, getAuthHeaders } from "../lib/api"
import {
  FileText, Link as LinkIcon, Mic, Upload,
  AlertTriangle, ShieldAlert, FileAudio, Loader2, ThumbsUp,
  ThumbsDown, Sparkles, ExternalLink, ChevronDown, Download,
  Globe, Search, ShieldCheck, Share2,
  Bookmark, RefreshCw, Copy, Printer, FileDown,
  Ban, Landmark, MessageCircle, Heart, CircleAlert
} from "lucide-react"
import { Button } from "../components/ui/button"
import { addBookmark } from "./Bookmarks"
import { useToast } from "../context/ToastContext"

/* ÔöÇÔöÇ Skeleton shimmer ÔöÇÔöÇ */
function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`animate-pulse bg-muted rounded-lg ${className}`} />
}

function SkeletonCard() {
  return (
    <div className="bg-secondary rounded-xl border border-border p-6 space-y-4 animate-fade-up">
      <div className="flex items-center gap-4">
        <Skeleton className="w-16 h-16 rounded-full" />
        <div className="space-y-2 flex-1"><Skeleton className="h-5 w-24" /><Skeleton className="h-3 w-32" /></div>
      </div>
      <Skeleton className="h-2 w-full" />
      <Skeleton className="h-2 w-4/5" />
      <Skeleton className="h-2 w-3/5" />
    </div>
  )
}




export function AnalyticsPage() {
  const { token } = useAuth()
  const { toast } = useToast()

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

  const [showExplain, setShowExplain] = useState(false)

  const [translateEnabled, setTranslateEnabled] = useState(false)
  const [safeBrowsing, setSafeBrowsing] = useState<any>(null)
  const [credibility, setCredibility] = useState<any>(null)
  const [recording, setRecording] = useState(false)
  const [processingMs, setProcessingMs] = useState(0)
  const [recentAnalyses, setRecentAnalyses] = useState<any[]>([])
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])
  // F4 FIX: AbortController to cancel in-flight requests
  const abortRef = useRef<AbortController | null>(null)

  const fileInputRef = useRef<HTMLInputElement>(null)

  // Cleanup on unmount — abort any pending requests
  useEffect(() => {
    return () => { abortRef.current?.abort() }
  }, [])

  // keyboard shortcut: Ctrl+Enter to analyze
  const handleKeyboard = useCallback((e: KeyboardEvent) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault()
      if (activeTab === 'text' && inputText.trim() && !loading) analyzeData(inputText)
      else if (activeTab === 'url' && inputUrl.trim() && !loading) document.querySelector<HTMLButtonElement>('[data-analyze-url]')?.click()
    }
  }, [activeTab, inputText, inputUrl, loading])
  useEffect(() => { document.addEventListener('keydown', handleKeyboard); return () => document.removeEventListener('keydown', handleKeyboard) }, [handleKeyboard])



  // AuthLayout already handles the !user redirect ÔÇö no need for a guard here

  /* ÔöÇÔöÇÔöÇ analysis helpers ÔöÇÔöÇÔöÇ */
  const analyzeData = async (text: string) => {
    // Cancel any in-flight requests before starting new one
    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller

    setError(""); setLoading(true); setResult(null)
    setAiResult(null); setGnewsResult(null); setFactResult(null); setFeedbackSent(false)
    const t0 = performance.now()
    try {
      const res = await fetch(`${API_BASE}/api/v1/analyze`, {
        method: "POST", headers: getAuthHeaders(),
        body: JSON.stringify({ text, sensitivity: sensitivity / 100, translate: translateEnabled }),
        signal: controller.signal
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || "Analysis failed")
      setProcessingMs(Math.round(performance.now() - t0))
      setResult(data)
      setRecentAnalyses(prev => [{ preview: text.slice(0, 60), prediction: data.prediction, confidence: data.confidence, ts: new Date().toISOString() }, ...prev].slice(0, 5))
      // fire secondary APIs in parallel (non-blocking)
      runSecondary(text, controller.signal)
    } catch (err: any) {
      if (err.name !== 'AbortError') setError(err.message)
    }
    finally { setLoading(false) }
  }

  const runSecondary = (text: string, signal: AbortSignal) => {
    const h = getAuthHeaders()
    // AI verification (Groq/Gemini)
    fetch(`${API_BASE}/api/v1/smart-verify`, { method: "POST", headers: h, body: JSON.stringify({ text }), signal })
      .then(r => r.ok ? r.json() : null).then(d => d && setAiResult(d)).catch(() => {})
    // GNews cross-reference
    fetch(`${API_BASE}/api/v1/gnews-search`, { method: "POST", headers: h, body: JSON.stringify({ text: text.slice(0, 200) }), signal })
      .then(r => r.ok ? r.json() : null).then(d => d && setGnewsResult(d)).catch(() => {})
    // Fact check
    fetch(`${API_BASE}/api/v1/fact-check`, { method: "POST", headers: h, body: JSON.stringify({ text: text.slice(0, 200) }), signal })
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
      // fire Safe Browsing + Source Credibility checks for URLs
      const h = getAuthHeaders()
      fetch(`${API_BASE}/api/v1/safe-browsing`, { method: "POST", headers: h, body: JSON.stringify({ url: inputUrl }) })
        .then(r => r.ok ? r.json() : null).then(d => d && setSafeBrowsing(d)).catch(() => {})
      fetch(`${API_BASE}/api/v1/source-credibility`, { method: "POST", headers: h, body: JSON.stringify({ url: inputUrl }) })
        .then(r => r.ok ? r.json() : null).then(d => d && setCredibility(d)).catch(() => {})
      await analyzeData(d.text)
    } catch (err: any) { setError(err.message); setLoading(false) }
  }

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const mr = new MediaRecorder(stream)
      chunksRef.current = []
      mr.ondataavailable = (e) => { if (e.data.size > 0) chunksRef.current.push(e.data) }
      mr.onstop = async () => {
        stream.getTracks().forEach(t => t.stop())
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' })
        if (blob.size < 1000) { setError('Recording too short.'); return }
        setLoading(true); setError('')
        const fd = new FormData(); fd.append('file', blob, 'recording.webm')
        try {
          const r = await fetch(`${API_BASE}/api/v1/transcribe`, {
            method: 'POST', headers: token ? { Authorization: `Bearer ${token}` } : {}, body: fd
          })
          const d = await r.json()
          if (!r.ok) throw new Error(d.detail || 'Transcription failed')
          if (!d.text) throw new Error('No speech detected.')
          setInputText(d.text); setActiveTab('text')
          await analyzeData(d.text)
        } catch (err: any) { setError(err.message); setLoading(false) }
      }
      mr.start()
      mediaRecorderRef.current = mr
      setRecording(true)
    } catch { setError('Microphone access denied.') }
  }

  const stopRecording = () => {
    mediaRecorderRef.current?.stop()
    setRecording(false)
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

  // §5 viral-loop metric: fire-and-forget, never blocks the share action.
  const logShare = (channel: string) => {
    try {
      fetch(`${API_BASE}/api/v1/share`, {
        method: "POST", headers: getAuthHeaders(),
        body: JSON.stringify({ channel }),
      }).catch(() => {})
    } catch { /* ignore */ }
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
      `VERIFAI ÔÇö Verification Report`, `Generated: ${new Date().toISOString()}`, ``,
      `Verdict: ${result.prediction}`, `Confidence: ${result.confidence.toFixed(1)}%`,
      `Tier: ${result.confidence_tier}`, `Red Flag Score: ${result.red_flag_score}/10`,
      `Fake Probability: ${(result.fake_probability*100).toFixed(1)}%`,
      `Real Probability: ${(result.real_probability*100).toFixed(1)}%`, ``,
      `--- Input Text ---`, inputText.slice(0,2000), ``,
      aiResult ? `--- AI Analysis ---\n${aiResult.analysis||'N/A'}` : '',
      gnewsResult?.articles?.length ? `--- Web Sources ---\n${gnewsResult.articles.map((a:any)=>`ÔÇó ${a.title} (${a.source?.name})`).join('\n')}` : '',
      factResult?.claims?.length ? `--- Fact Checks ---\n${factResult.claims.map((c:any)=>`ÔÇó ${c.text} ÔÇö ${c.claimReview?.[0]?.textualRating||'Unrated'}`).join('\n')}` : '',
    ].filter(Boolean).join('\n')
    const blob = new Blob([lines], {type:'text/plain'})
    const a = document.createElement('a'); a.href=URL.createObjectURL(blob); a.download='verifai-report.txt'; a.click()
  }




  return (
    <div className="bg-background p-6 md:p-8 text-foreground">
      <div className="max-w-6xl mx-auto">
        {/* ÔöÇÔöÇ Executive Brief Card ÔöÇÔöÇ */}
        <div className="card-enterprise p-6 mb-6 relative overflow-hidden">
          <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-primary via-accent to-primary" />
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <h1 className="text-2xl font-heading font-extrabold tracking-tight">Analysis Center</h1>
              <p className="text-sm text-muted-foreground mt-0.5">Verify news articles, URLs, and audio clips for misinformation.</p>
            </div>
            <div className="flex items-center gap-2">
              <span className="stat-pill"><span className="w-2 h-2 rounded-full bg-[#4ADE80] animate-pulse inline-block mr-1.5" />System Online</span>
              <span className="stat-pill font-mono text-[10px]">{new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}</span>
            </div>
          </div>
        </div>



        <div className="space-y-8">
          {/* Input Panel — centered */}
          <div className="max-w-3xl mx-auto">
            <div className="card-enterprise overflow-hidden">
              {/* Tabs */}
              <div className="flex border-b border-border">
                {([["text", FileText, "Text"], ["url", LinkIcon, "URL"], ["audio", Mic, "Audio"]] as const).map(([key, Icon, label]) => (
                  <button key={key} onClick={() => setActiveTab(key as any)}
                    className={`flex-1 py-3.5 text-sm font-medium flex items-center justify-center gap-2 transition-all relative ${activeTab === key ? 'text-primary' : 'text-muted-foreground hover:text-foreground'}`}>
                    <Icon className="w-4 h-4" /> {label}
                    {activeTab === key && <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-primary" />}
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

                    {/* Feature 2: Char count + Sensitivity + Translate */}
                    <div className="flex items-center justify-between mt-2 mb-4 gap-3 flex-wrap">
                      <span className="text-xs text-muted-foreground">
                        {inputText.length} / 5,000 chars
                        {inputText.trim() && <> · {inputText.trim().split(/\s+/).length} words · ~{Math.max(1, Math.ceil(inputText.trim().split(/\s+/).length / 200))} min read</>}
                      </span>
                      <div className="flex items-center gap-4">
                        <label className="flex items-center gap-1.5 cursor-pointer">
                          <input type="checkbox" checked={translateEnabled} onChange={e => setTranslateEnabled(e.target.checked)}
                            className="w-3.5 h-3.5 accent-primary cursor-pointer" />
                          <span className="text-xs text-muted-foreground">Translate</span>
                        </label>
                        <div className="flex items-center gap-1.5">
                          <span className="text-xs text-muted-foreground">Sensitivity:</span>
                        <input type="range" min={0} max={100} value={sensitivity}
                          onChange={e => setSensitivity(+e.target.value)}
                          className="w-20 h-1 accent-primary cursor-pointer" />
                          <span className="text-xs font-medium text-primary w-8">{(sensitivity / 100).toFixed(2)}</span>
                        </div>
                      </div>
                    </div>

                    {/* Input quality warnings */}
                    {inputText.trim().length > 0 && (() => {
                      const txt = inputText.trim()
                      const warns: { icon: string; msg: string; level: 'warn' | 'error' }[] = []
                      if (txt.length < 50) warns.push({ icon: '⚠️', msg: 'Very short text — results may be unreliable', level: 'warn' })
                      else if (txt.length < 150) warns.push({ icon: '💡', msg: 'Short text — longer articles yield better accuracy', level: 'warn' })
                      const capsRatio = (txt.replace(/[^A-Z]/g, '').length) / Math.max(txt.replace(/[^a-zA-Z]/g, '').length, 1)
                      if (capsRatio > 0.6 && txt.length > 20) warns.push({ icon: '🔡', msg: 'Excessive caps detected — common in clickbait', level: 'warn' })
                      const urlCount = (txt.match(/https?:\/\//g) || []).length
                      if (urlCount > 3) warns.push({ icon: '🔙', msg: `${urlCount} URLs found — consider using the URL tab instead`, level: 'warn' })
                      const words = txt.split(/\s+/)
                      const unique = new Set(words.map(w => w.toLowerCase()))
                      if (words.length > 20 && unique.size / words.length < 0.4) warns.push({ icon: '🔜', msg: 'Repetitive text detected — may skew analysis', level: 'warn' })
                      if (/[\u0900-\u097F\u0980-\u09FF\u0600-\u06FF\u4E00-\u9FFF\u3040-\u309F]/.test(txt) && !translateEnabled)
                        warns.push({ icon: '🌐', msg: 'Non-English script detected — enable "Translate" for better results', level: 'error' })
                      return warns.length > 0 ? (
                        <div className="flex flex-wrap gap-1.5 mb-3">
                          {warns.map((w, i) => (
                            <span key={i} className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-[10px] font-medium ${
                              w.level === 'error' ? 'bg-destructive/10 text-destructive' : 'bg-accent/10 text-accent'}`}>
                              {w.icon} {w.msg}
                            </span>
                          ))}
                        </div>
                      ) : null
                    })()}

                    <button className="w-full btn-gradient rounded-xl py-3.5 text-sm font-semibold disabled:opacity-50 disabled:cursor-not-allowed" onClick={handleAnalyzeText} disabled={loading}>
                      {loading ? <span className="flex items-center justify-center gap-2"><Loader2 className="w-4 h-4 animate-spin" /> Analyzing...</span> : "Analyze Content →"}
                    </button>
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
                    <div className={`w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4 transition-colors ${recording ? 'bg-destructive/20 text-destructive animate-pulse' : 'bg-primary/10 text-primary'}`}>
                      {recording ? <Mic className="w-8 h-8" /> : <FileAudio className="w-8 h-8" />}
                    </div>
                    <h3 className="text-lg font-medium mb-2">{recording ? 'Recording...' : 'Voice Input'}</h3>
                    <p className="text-sm text-muted-foreground mb-6 max-w-sm mx-auto">
                      {recording ? 'Speak clearly into your microphone. Click Stop when done.' : 'Record live or upload an audio file. We\'ll transcribe and analyze.'}
                    </p>
                    <input type="file" accept="audio/*" className="hidden" ref={fileInputRef} onChange={handleFileUpload} />
                    <div className="flex gap-3 justify-center">
                      {recording ? (
                        <Button variant="outline" size="lg" onClick={stopRecording} className="border-destructive/50 text-destructive hover:bg-destructive/10">
                          ÔÅ╣ Stop Recording
                        </Button>
                      ) : (
                        <>
                          <Button variant="outline" size="lg" onClick={startRecording} disabled={loading}>
                            <Mic className="w-4 h-4 mr-2" /> Record
                          </Button>
                          <Button variant="outline" size="lg" onClick={() => fileInputRef.current?.click()} disabled={loading}>
                            {loading
                              ? <span className="flex items-center gap-2"><Loader2 className="w-4 h-4 animate-spin" /> Processing...</span>
                              : <span className="flex items-center gap-2"><Upload className="w-4 h-4" /> Upload File</span>}
                          </Button>
                        </>
                      )}
                    </div>
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

          {/* Results Panel — full width */}
          <div className="flex flex-col gap-6">
            {result ? (
              <>
                {/* Verdict card */}
                <div className={`card-enterprise p-6 animate-fade-up relative overflow-hidden ${result.prediction === "FAKE" ? "border-verdict-fake" : "border-verdict-real"}`}>
                  <div className={`absolute top-0 left-0 right-0 h-1 ${result.prediction === "FAKE" ? "bg-destructive" : "bg-[#4ADE80]"}`} />
                  <div className="flex items-center gap-4 mb-6">
                    {/* Confidence gauge */}
                    <div className="relative w-16 h-16 shrink-0">
                      <svg viewBox="0 0 80 80" className="w-full h-full -rotate-90">
                        <circle cx="40" cy="40" r="34" fill="none" stroke="hsl(var(--border))" strokeWidth="6" />
                        <circle cx="40" cy="40" r="34" fill="none"
                          stroke={result.prediction === "FAKE" ? "hsl(var(--destructive))" : "#4ADE80"}
                          strokeWidth="6" strokeLinecap="round"
                          strokeDasharray={`${2 * Math.PI * 34}`}
                          strokeDashoffset={`${2 * Math.PI * 34 * (1 - result.confidence / 100)}`}
                          className="transition-all duration-1000" />
                      </svg>
                      <span className="absolute inset-0 flex items-center justify-center text-sm font-heading font-bold">{Math.round(result.confidence)}%</span>
                    </div>
                    <div>
                      <h2 className="text-xl font-heading font-extrabold uppercase tracking-wide">{result.prediction}</h2>
                      <p className="text-xs text-muted-foreground font-mono">{result.confidence_tier} · {result.confidence.toFixed(1)}%</p>
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
                          <span className="text-muted-foreground text-xs">{b.label}</span>
                          <span className="font-heading font-bold text-xs">{b.fmt ?? `${(b.val * 100).toFixed(1)}%`}</span>
                        </div>
                        <div className="h-2 w-full bg-background rounded-full overflow-hidden">
                          <div className={`h-full ${b.color} transition-all duration-500 rounded-full`} style={{ width: `${(b.fmt ? b.val : b.val) * 100}%` }} />
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
                        <AlertTriangle className="w-3.5 h-3.5 inline mr-1" /> {result.input_quality === "short_claim" ? "Very short input — confidence capped at 60%." : "Short headline — confidence capped at 80%."} Paste the full article for best results.
                      </p>
                    </div>
                  )}

                  <div className="mt-3 flex items-center justify-between">
                    <span className="text-[11px] text-muted-foreground/50">Model v{result.model_version} · {result.timestamp?.split("T")[0]} · {processingMs < 1000 ? `${processingMs}ms` : `${(processingMs / 1000).toFixed(1)}s`}</span>
                    <div className="flex items-center gap-3">
                      <button onClick={() => { addBookmark(result, inputText); toast('Bookmarked!', 'success') }}
                        className="text-[11px] text-muted-foreground hover:text-primary flex items-center gap-1 transition-colors">
                        <Bookmark className="w-3 h-3" /> Save
                      </button>
                      <button onClick={() => analyzeData(inputText)}
                        className="text-[11px] text-primary hover:underline flex items-center gap-1">
                        <RefreshCw className="w-3 h-3" /> Re-analyze
                      </button>
                    </div>
                  </div>
                </div>



                {/* Secondary panels in 2-column grid */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

                {/* Feature 4: AI Analysis panel */}
                {aiResult && (
                  <div className="card-enterprise p-5 animate-fade-up" style={{ animationDelay: "0.25s" }}>
                    <div className="flex items-center gap-2 mb-3">
                      <Sparkles className="w-4 h-4 text-[#a78bfa]" />
                      <h3 className="text-sm font-semibold">AI Verification</h3>
                      {aiResult.is_indic && (
                        <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-blue-500/15 text-blue-400 font-medium uppercase">
                          {aiResult.detected_lang === 'hinglish' ? 'Hinglish' : aiResult.detected_lang?.toUpperCase()} detected
                        </span>
                      )}
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
                <div className="card-enterprise p-5 animate-fade-up" style={{ animationDelay: "0.3s" }}>
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

                {/* Share Results */}
                <div className="card-enterprise p-5 animate-fade-up" style={{ animationDelay: "0.32s" }}>
                  <h3 className="text-sm font-semibold mb-3 flex items-center gap-2"><Share2 className="w-4 h-4" /> Share Results</h3>
                  <div className="flex flex-wrap gap-2">
                    <Button variant="outline" size="sm" className="flex-1 min-w-[120px]" onClick={() => {
                      const url = result.claim_hash ? `https://fake-news-detector-8djq.onrender.com/claim/${result.claim_hash}` : 'https://fake-news-detector-8djq.onrender.com';
                      navigator.clipboard.writeText(url).then(() => {
                        logShare('copy')
                      })
                    }}>
                      <Copy className="w-3.5 h-3.5 mr-1.5" /> Copy Link
                    </Button>
                    <Button variant="outline" size="sm" className="flex-1 min-w-[120px]" onClick={() => {
                      const url = result.claim_hash ? `https://fake-news-detector-8djq.onrender.com/claim/${result.claim_hash}` : 'https://fake-news-detector-8djq.onrender.com';
                      const text = encodeURIComponent(`VERIFAI analysis: ${result.prediction} (${result.confidence.toFixed(1)}%) — See full report: ${url}`)
                      window.open(`https://wa.me/?text=${text}`, '_blank')
                      logShare('whatsapp')
                    }}>
                      <svg className="w-3.5 h-3.5 mr-1.5" viewBox="0 0 24 24" fill="currentColor"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/></svg>
                      WhatsApp
                    </Button>
                    <Button variant="outline" size="sm" className="flex-1 min-w-[120px]" onClick={() => {
                      const url = result.claim_hash ? `https://fake-news-detector-8djq.onrender.com/claim/${result.claim_hash}` : 'https://fake-news-detector-8djq.onrender.com';
                      const text = encodeURIComponent(`Just verified a claim using @VerifAI_app — ${result.prediction} with ${result.confidence.toFixed(1)}% confidence!\n\nFull report:`)
                      window.open(`https://twitter.com/intent/tweet?text=${text}&url=${encodeURIComponent(url)}`, '_blank')
                      logShare('twitter')
                    }}>
                      <svg className="w-3.5 h-3.5 mr-1.5" viewBox="0 0 24 24" fill="currentColor"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>
                      Tweet
                    </Button>
                    <Button variant="outline" size="sm" className="flex-1 text-amber-400 border-amber-500/30 hover:bg-amber-500/10" onClick={() => {
                      window.open('https://razorpay.me/@koushalkishorray', '_blank')
                      logShare('donate')
                    }}>
                      <Heart className="w-3.5 h-3.5 mr-1.5" /> Support
                    </Button>
                  </div>
                </div>

                {/* Feature 6: Explainable AI Insights */}
                <div className="card-enterprise overflow-hidden animate-fade-up" style={{ animationDelay: "0.35s" }}>
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
                                <CircleAlert className="w-3.5 h-3.5 text-destructive mt-0.5 shrink-0" />
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
                  <div className="card-enterprise p-5 animate-fade-up" style={{ animationDelay: "0.4s" }}>
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
                  <div className="card-enterprise p-5 animate-fade-up" style={{ animationDelay: "0.45s" }}>
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

                {/* Safe Browsing panel */}
                {safeBrowsing && (
                  <div className="card-enterprise p-5 animate-fade-up" style={{ animationDelay: "0.48s" }}>
                    <div className="flex items-center gap-2 mb-3">
                      <ShieldCheck className="w-4 h-4 text-[#4ADE80]" />
                      <h3 className="text-sm font-semibold">Safe Browsing</h3>
                      <span className={`ml-auto text-xs px-2 py-0.5 rounded-full font-medium ${
                        safeBrowsing.safe ? 'bg-[#4ADE80]/15 text-[#4ADE80]' : 'bg-destructive/15 text-destructive'}`}>
                        {safeBrowsing.safe ? 'SAFE' : 'THREATS FOUND'}
                      </span>
                    </div>
                    <p className="text-xs text-muted-foreground">
                      {safeBrowsing.safe
                        ? 'URL passed all safety checks. No malware, phishing, or social engineering detected.'
                        : `Threats: ${safeBrowsing.threats?.join(', ') || 'Unknown'}. Exercise caution.`}
                    </p>
                  </div>
                )}

                {/* Source Credibility panel */}
                {credibility && (
                  <div className="card-enterprise p-5 animate-fade-up" style={{ animationDelay: "0.49s" }}>
                    <div className="flex items-center gap-2 mb-3">
                      <Globe className="w-4 h-4 text-[#a78bfa]" />
                      <h3 className="text-sm font-semibold">Source Credibility</h3>
                      <span className={`ml-auto text-xs px-2 py-0.5 rounded-full font-medium ${
                        (credibility.score ?? 50) >= 70 ? 'bg-[#4ADE80]/15 text-[#4ADE80]' :
                        (credibility.score ?? 50) >= 40 ? 'bg-accent/15 text-accent' :
                        'bg-destructive/15 text-destructive'}`}>
                        {credibility.score ?? 50}/100
                      </span>
                    </div>
                    <div className="space-y-2">
                      <div className="h-2 w-full bg-background rounded-full overflow-hidden">
                        <div className={`h-full transition-all duration-500 ${
                          (credibility.score ?? 50) >= 70 ? 'bg-[#4ADE80]' : (credibility.score ?? 50) >= 40 ? 'bg-accent' : 'bg-destructive'
                        }`} style={{ width: `${credibility.score ?? 50}%` }} />
                      </div>
                      <p className="text-xs text-muted-foreground">
                        {credibility.domain && <><span className="font-medium text-foreground">{credibility.domain}</span> · </>}
                        {credibility.category || 'Unknown category'}
                        {credibility.description && ` · ${credibility.description}`}
                      </p>
                    </div>
                  </div>
                )}

                {/* Feature 9: Export Report */}
                <div className="card-enterprise p-5 animate-fade-up" style={{ animationDelay: "0.5s" }}>
                  <h3 className="text-sm font-semibold mb-3 flex items-center gap-2"><Download className="w-4 h-4" /> Export Report</h3>
                  <div className="flex gap-3">
                    <Button variant="outline" size="sm" className="flex-1" onClick={exportText}>
                      <FileDown className="w-3.5 h-3.5 mr-1.5" /> Export as Text
                    </Button>
                    <Button variant="outline" size="sm" className="flex-1" onClick={() => { window.print() }}>
                      <Printer className="w-3.5 h-3.5 mr-1.5" /> Print / PDF
                    </Button>
                  </div>
                </div>



                {/* India Threat Scanner */}
                {(() => {
                  const txt = inputText.toLowerCase()
                  const threats: { type: string; label: string; desc: string }[] = []
                  if (/upi|paytm|phonepe|google\s*pay|bhim|gpay/.test(txt) && /reward|prize|won|cashback|offer|rupee|lakhs?|crore/.test(txt))
                    threats.push({ type: "upi", label: "UPI Fraud Alert", desc: "Contains UPI app mentions with prize/reward language — common payment scam pattern." })
                  if (/government|modi|scheme|yojana|pm[\s-]kisan|aadhaar|ayushman|pradhan\s*mantri/.test(txt) && /apply|register|click|link|form|free|subsidy/.test(txt))
                    threats.push({ type: "govt", label: "Fake Govt Scheme", desc: "References government programs with suspicious call-to-action — verify on official .gov.in sites." })
                  if (/forward|share|whatsapp|viral|send\s*to|pass\s*on|circulating/.test(txt))
                    threats.push({ type: "forward", label: "WhatsApp Forward", desc: "Text shows forwarded message patterns — chain messages often contain unverified claims." })
                  if (/ayurved|desi\s*ilaj|home\s*remed|cure\s*for|miracle|100%\s*effective/.test(txt) && /cancer|diabetes|covid|corona/.test(txt))
                    threats.push({ type: "health", label: "Health Misinformation", desc: "Contains miracle cure claims for serious diseases — consult qualified medical professionals." })

                  return threats.length > 0 ? (
                    <div className="bg-secondary rounded-xl border border-accent/30 p-5 animate-fade-up" style={{ animationDelay: "0.6s" }}>
                      <h3 className="text-sm font-semibold mb-3 flex items-center gap-2">
                        <ShieldAlert className="w-4 h-4 text-accent" /> India Threat Scanner
                        <span className="ml-auto text-xs px-2 py-0.5 rounded-full bg-accent/15 text-accent font-medium">{threats.length} ALERT{threats.length > 1 ? 'S' : ''}</span>
                      </h3>
                      <div className="space-y-2.5">
                        {threats.map((t, i) => (
                          <div key={i} className="bg-background rounded-lg p-3 flex items-start gap-2.5">
                            <span className="text-lg">{t.type === 'upi' ? <Ban className="w-5 h-5 text-destructive" /> : t.type === 'govt' ? <Landmark className="w-5 h-5 text-accent" /> : t.type === 'forward' ? <MessageCircle className="w-5 h-5 text-[#38bdf8]" /> : <Heart className="w-5 h-5 text-destructive" />}</span>
                            <div>
                              <p className="text-xs font-semibold text-accent">{t.label}</p>
                              <p className="text-[11px] text-muted-foreground leading-relaxed">{t.desc}</p>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : null
                })()}
                </div>{/* close 2-col grid */}
              </>
            ) : loading ? (
              /* Skeleton loaders while analyzing */
              <div className="flex flex-col gap-6">
                <SkeletonCard />
                <div className="grid grid-cols-2 gap-3">
                  <Skeleton className="h-28 rounded-xl" />
                  <Skeleton className="h-28 rounded-xl" />
                  <Skeleton className="h-28 rounded-xl" />
                  <Skeleton className="h-28 rounded-xl" />
                </div>
                <Skeleton className="h-24 rounded-xl" />
              </div>
            ) : (
              <div className="bg-background border border-border border-dashed rounded-xl p-8 flex flex-col items-center justify-center text-center h-full min-h-[300px]">
                <ShieldAlert className="w-12 h-12 text-muted mb-4" />
                <h3 className="text-foreground font-medium mb-1">No Analysis Yet</h3>
                <p className="text-muted-foreground text-sm max-w-[200px]">
                  Submit text, a URL, or an audio file to see the AI verification results here.
                </p>
                <p className="text-muted-foreground/50 text-[10px] mt-3">Tip: Press Ctrl+Enter to analyze</p>
              </div>
            )}
          </div>
        </div>

        {/* Recent Analyses widget */}
        {recentAnalyses.length > 0 && (
          <div className="mt-8 bg-secondary border border-border rounded-xl p-5">
            <h3 className="text-sm font-semibold mb-3">Recent (this session)</h3>
            <div className="space-y-2">
              {recentAnalyses.map((r, i) => (
                <div key={i} className="flex items-center gap-3 bg-background rounded-lg px-3 py-2">
                  <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full ${r.prediction === 'FAKE' ? 'bg-destructive/15 text-destructive' : 'bg-[#4ADE80]/15 text-[#4ADE80]'}`}>{r.prediction}</span>
                  <span className="text-xs text-muted-foreground truncate flex-1">{r.preview}...</span>
                  <span className="text-[10px] text-muted-foreground shrink-0">{r.confidence?.toFixed(0)}%</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Suspicious text highlighting */}
        {result && inputText.trim() && (() => {
          const suspiciousPatterns = [
            { re: /\b(breaking|urgent|shocking|exclusive|alert)\b/gi, label: 'Sensational' },
            { re: /\b(sources say|reportedly|allegedly|rumor|unconfirmed)\b/gi, label: 'Unverified' },
            { re: /\b(miracle|100%|guaranteed|secret|they don'?t want you to know)\b/gi, label: 'Clickbait' },
          ]
          const found: { word: string; label: string }[] = []
          suspiciousPatterns.forEach(p => {
            let m; while ((m = p.re.exec(inputText)) !== null) found.push({ word: m[0], label: p.label })
          })
          return found.length > 0 ? (
            <div className="mt-4 bg-secondary border border-accent/30 rounded-xl p-4">
              <h4 className="text-xs font-semibold mb-2 text-accent"><AlertTriangle className="w-3.5 h-3.5 inline mr-1" /> Suspicious Keywords Found</h4>
              <div className="flex flex-wrap gap-1.5">
                {found.map((f, i) => (
                  <span key={i} className="inline-flex items-center gap-1 px-2 py-0.5 bg-accent/10 text-accent rounded-full text-[10px] font-medium">
                    "{f.word}" <span className="text-muted-foreground">({f.label})</span>
                  </span>
                ))}
              </div>
            </div>
          ) : null
        })()}
      </div>
    </div>
  )
}
