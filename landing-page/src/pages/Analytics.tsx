import { useState, useRef, useEffect, useCallback } from "react"
import { useAuth } from "../context/AuthContext"
import { API_BASE, getAuthHeaders } from "../lib/api"
import { useIsMobile } from "../hooks/useIsMobile"
import { useToast } from "../context/ToastContext"
import { addBookmark } from "./Bookmarks"
import { AnalyticsDesktop } from "./desktop/AnalyticsDesktop"
import { AnalyticsMobile } from "./mobile/AnalyticsMobile"

/** Shared prop interface for desktop/mobile analytics views */
export interface AnalyticsViewProps {
  activeTab: "text" | "url" | "audio"
  setActiveTab: (tab: "text" | "url" | "audio") => void
  inputText: string
  setInputText: (v: string) => void
  inputUrl: string
  setInputUrl: (v: string) => void
  sensitivity: number
  setSensitivity: (v: number) => void
  loading: boolean
  error: string
  result: any
  aiResult: any
  gnewsResult: any
  factResult: any
  feedbackSent: boolean
  showExplain: boolean
  setShowExplain: (v: boolean) => void
  translateEnabled: boolean
  setTranslateEnabled: (v: boolean) => void
  safeBrowsing: any
  credibility: any
  recording: boolean
  processingMs: number
  recentAnalyses: any[]
  fileInputRef: React.RefObject<HTMLInputElement | null>
  handleAnalyzeText: () => void
  handleAnalyzeUrl: () => void
  startRecording: () => void
  stopRecording: () => void
  handleFileUpload: (e: React.ChangeEvent<HTMLInputElement>) => void
  sendFeedback: (correct: boolean) => void
  exportText: () => void
  logShare: (channel: string) => void
  analyzeData: (text: string) => void
  addBookmarkFn: (result: any, text: string) => void
  toast: (msg: string, type?: "error" | "success" | "info") => void
}

export function AnalyticsPage() {
  const { token } = useAuth()
  const { toast } = useToast()
  const isMobile = useIsMobile()

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
  // AbortController to cancel in-flight requests
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

  // AuthLayout already handles the !user redirect — no need for a guard here

  /* ——— analysis helpers ——— */
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

  // viral-loop metric: fire-and-forget, never blocks the share action.
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

  const viewProps: AnalyticsViewProps = {
    activeTab, setActiveTab, inputText, setInputText, inputUrl, setInputUrl,
    sensitivity, setSensitivity, loading, error, result,
    aiResult, gnewsResult, factResult, feedbackSent,
    showExplain, setShowExplain, translateEnabled, setTranslateEnabled,
    safeBrowsing, credibility, recording, processingMs, recentAnalyses,
    fileInputRef, handleAnalyzeText, handleAnalyzeUrl, startRecording, stopRecording,
    handleFileUpload, sendFeedback, exportText, logShare, analyzeData,
    addBookmarkFn: addBookmark, toast
  }

  return isMobile ? <AnalyticsMobile {...viewProps} /> : <AnalyticsDesktop {...viewProps} />
}
