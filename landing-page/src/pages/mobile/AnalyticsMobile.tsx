import {
  FileText, Link as LinkIcon, Mic, Upload,
  AlertTriangle, ShieldAlert, FileAudio, Loader2, ThumbsUp,
  ThumbsDown, Sparkles, ExternalLink, ChevronDown,
  Globe, Search, ShieldCheck, Share2,
  Bookmark, RefreshCw, Copy, FileDown,
  Ban, Landmark, MessageCircle, CircleAlert
} from "lucide-react"
import { Button } from "../../components/ui/button"
import type { AnalyticsViewProps } from "../Analytics"

export function AnalyticsMobile({
  activeTab, setActiveTab, inputText, setInputText, inputUrl, setInputUrl,
  sensitivity, setSensitivity, loading, error, result,
  aiResult, gnewsResult, factResult, feedbackSent,
  showExplain, setShowExplain, translateEnabled, setTranslateEnabled,
  safeBrowsing, recording, processingMs, recentAnalyses,
  fileInputRef, handleAnalyzeText, handleAnalyzeUrl, startRecording, stopRecording,
  handleFileUpload, sendFeedback, exportText, logShare, analyzeData,
  addBookmarkFn, toast
}: AnalyticsViewProps) {

  return (
    <div className="bg-background px-4 py-4 text-foreground w-full max-w-full overflow-x-hidden">
      {/* Compact header */}
      <div className="card-enterprise p-4 mb-4 relative overflow-hidden">
        <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-primary via-accent to-primary" />
        <h1 className="text-lg font-heading font-extrabold tracking-tight">Analyze</h1>
        <p className="text-[11px] text-muted-foreground mt-0.5">Verify news, URLs & audio</p>
      </div>

      <div className="space-y-4">
        {/* Input Panel */}
        <div className="card-enterprise overflow-hidden">
          {/* Tabs — compact */}
          <div className="flex border-b border-border">
            {([["text", FileText, "Text"], ["url", LinkIcon, "URL"], ["audio", Mic, "Audio"]] as const).map(([key, Icon, label]) => (
              <button key={key} onClick={() => setActiveTab(key as any)}
                className={`flex-1 py-3 text-xs font-medium flex items-center justify-center gap-1.5 transition-all relative ${activeTab === key ? 'text-primary' : 'text-muted-foreground'}`}>
                <Icon className="w-3.5 h-3.5" /> {label}
                {activeTab === key && <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-primary" />}
              </button>
            ))}
          </div>

          <div className="p-4">
            {/* Text tab */}
            {activeTab === "text" && (
              <div className="animate-fade-in">
                <textarea placeholder="Paste the news article here..."
                  className="w-full h-36 bg-background border border-border rounded-lg p-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 resize-none"
                  value={inputText} onChange={e => setInputText(e.target.value)} maxLength={5000} />

                <div className="flex items-center justify-between mt-2 mb-3 gap-2">
                  <span className="text-[10px] text-muted-foreground">{inputText.length}/5000</span>
                  <div className="flex items-center gap-3">
                    <label className="flex items-center gap-1 cursor-pointer">
                      <input type="checkbox" checked={translateEnabled} onChange={e => setTranslateEnabled(e.target.checked)}
                        className="w-3 h-3 accent-primary cursor-pointer" />
                      <span className="text-[10px] text-muted-foreground">Translate</span>
                    </label>
                    <div className="flex items-center gap-1">
                      <span className="text-[10px] text-muted-foreground">Sens:</span>
                      <input type="range" min={0} max={100} value={sensitivity}
                        onChange={e => setSensitivity(+e.target.value)}
                        className="w-14 h-1 accent-primary cursor-pointer" />
                      <span className="text-[10px] font-medium text-primary">{(sensitivity / 100).toFixed(1)}</span>
                    </div>
                  </div>
                </div>

                {/* Input quality warnings — compact */}
                {inputText.trim().length > 0 && (() => {
                  const txt = inputText.trim()
                  const warns: string[] = []
                  if (txt.length < 50) warns.push('⚠️ Very short text')
                  if (/[\u0900-\u097F\u0980-\u09FF\u0600-\u06FF\u4E00-\u9FFF]/.test(txt) && !translateEnabled) warns.push('🌐 Non-English — enable Translate')
                  return warns.length > 0 ? (
                    <div className="flex flex-wrap gap-1 mb-2">
                      {warns.map((w, i) => (
                        <span key={i} className="text-[9px] px-1.5 py-0.5 rounded-full bg-accent/10 text-accent">{w}</span>
                      ))}
                    </div>
                  ) : null
                })()}

                <button className="w-full btn-gradient rounded-xl py-3 text-sm font-semibold disabled:opacity-50" onClick={handleAnalyzeText} disabled={loading}>
                  {loading ? <span className="flex items-center justify-center gap-2"><Loader2 className="w-4 h-4 animate-spin" /> Analyzing...</span> : "Analyze →"}
                </button>
              </div>
            )}

            {/* URL tab */}
            {activeTab === "url" && (
              <div className="animate-fade-in space-y-3">
                <input type="url" placeholder="https://example.com/article"
                  className="w-full bg-background border border-border rounded-lg px-3 py-2.5 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/50"
                  value={inputUrl} onChange={e => setInputUrl(e.target.value)} />
                <Button className="w-full" size="default" onClick={handleAnalyzeUrl} disabled={loading} data-analyze-url>
                  {loading ? <span className="flex items-center gap-2"><Loader2 className="w-4 h-4 animate-spin" /> Fetching...</span> : "Analyze URL"}
                </Button>
              </div>
            )}

            {/* Audio tab */}
            {activeTab === "audio" && (
              <div className="animate-fade-in text-center py-6">
                <div className={`w-14 h-14 rounded-full flex items-center justify-center mx-auto mb-3 transition-colors ${recording ? 'bg-destructive/20 text-destructive animate-pulse' : 'bg-primary/10 text-primary'}`}>
                  {recording ? <Mic className="w-7 h-7" /> : <FileAudio className="w-7 h-7" />}
                </div>
                <h3 className="text-base font-medium mb-1">{recording ? 'Recording...' : 'Voice Input'}</h3>
                <p className="text-xs text-muted-foreground mb-4 max-w-[200px] mx-auto">
                  {recording ? 'Speak clearly. Tap Stop when done.' : 'Record or upload audio to analyze.'}
                </p>
                <input type="file" accept="audio/*" className="hidden" ref={fileInputRef} onChange={handleFileUpload} />
                <div className="flex gap-2 justify-center">
                  {recording ? (
                    <Button variant="outline" size="default" onClick={stopRecording} className="border-destructive/50 text-destructive">
                      ■ Stop
                    </Button>
                  ) : (
                    <>
                      <Button variant="outline" size="default" onClick={startRecording} disabled={loading}>
                        <Mic className="w-4 h-4 mr-1" /> Record
                      </Button>
                      <Button variant="outline" size="default" onClick={() => fileInputRef.current?.click()} disabled={loading}>
                        <Upload className="w-4 h-4 mr-1" /> Upload
                      </Button>
                    </>
                  )}
                </div>
              </div>
            )}

            {error && (
              <div className="mt-3 p-2.5 bg-destructive/10 border border-destructive/30 text-destructive text-xs rounded-lg flex items-start gap-2">
                <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" /><p>{error}</p>
              </div>
            )}
          </div>
        </div>

        {/* Results — single column, stacked */}
        {result ? (
          <div className="space-y-3">
            {/* Verdict card — compact */}
            <div className={`card-enterprise p-4 animate-fade-up relative overflow-hidden ${result.prediction === "FAKE" ? "border-verdict-fake" : "border-verdict-real"}`}>
              <div className={`absolute top-0 left-0 right-0 h-1 ${result.prediction === "FAKE" ? "bg-destructive" : "bg-[#4ADE80]"}`} />
              <div className="flex items-center gap-3 mb-4">
                <div className="relative w-14 h-14 shrink-0">
                  <svg viewBox="0 0 80 80" className="w-full h-full -rotate-90">
                    <circle cx="40" cy="40" r="34" fill="none" stroke="hsl(var(--border))" strokeWidth="6" />
                    <circle cx="40" cy="40" r="34" fill="none"
                      stroke={result.prediction === "FAKE" ? "hsl(var(--destructive))" : "#4ADE80"}
                      strokeWidth="6" strokeLinecap="round"
                      strokeDasharray={`${2 * Math.PI * 34}`}
                      strokeDashoffset={`${2 * Math.PI * 34 * (1 - result.confidence / 100)}`}
                      className="transition-all duration-1000" />
                  </svg>
                  <span className="absolute inset-0 flex items-center justify-center text-xs font-heading font-bold">{Math.round(result.confidence)}%</span>
                </div>
                <div>
                  <h2 className="text-lg font-heading font-extrabold uppercase">{result.prediction}</h2>
                  <p className="text-[10px] text-muted-foreground font-mono">{result.confidence_tier} · {result.confidence.toFixed(1)}%</p>
                </div>
              </div>

              {/* Probability bars — compact */}
              <div className="space-y-2.5">
                {[
                  { label: "Fake", val: result.fake_probability, color: "bg-destructive" },
                  { label: "Real", val: result.real_probability, color: "bg-[#4ADE80]" },
                  { label: "Red Flags", val: result.red_flag_score / 10, color: "bg-accent", fmt: `${result.red_flag_score}/10` },
                ].map((b, i) => (
                  <div key={i}>
                    <div className="flex justify-between mb-0.5">
                      <span className="text-[10px] text-muted-foreground">{b.label}</span>
                      <span className="text-[10px] font-bold">{b.fmt ?? `${(b.val * 100).toFixed(0)}%`}</span>
                    </div>
                    <div className="h-1.5 w-full bg-background rounded-full overflow-hidden">
                      <div className={`h-full ${b.color} rounded-full transition-all duration-500`} style={{ width: `${(b.fmt ? b.val : b.val) * 100}%` }} />
                    </div>
                  </div>
                ))}
              </div>

              {/* Indicator words */}
              {(result.fake_indicator_words?.length > 0 || result.real_indicator_words?.length > 0) && (
                <div className="mt-3 pt-3 border-t border-border">
                  <div className="flex flex-wrap gap-1">
                    {result.fake_indicator_words?.slice(0, 3).map((w: string, i: number) => (
                      <span key={`f${i}`} className="text-[9px] bg-destructive/15 text-destructive px-1.5 py-0.5 rounded-full">{w}</span>
                    ))}
                    {result.real_indicator_words?.slice(0, 3).map((w: string, i: number) => (
                      <span key={`r${i}`} className="text-[9px] bg-[#4ADE80]/15 text-[#4ADE80] px-1.5 py-0.5 rounded-full">{w}</span>
                    ))}
                  </div>
                </div>
              )}

              {/* Actions row */}
              <div className="mt-3 flex items-center justify-between">
                <span className="text-[9px] text-muted-foreground/50">{processingMs < 1000 ? `${processingMs}ms` : `${(processingMs / 1000).toFixed(1)}s`}</span>
                <div className="flex items-center gap-2">
                  <button onClick={() => { addBookmarkFn(result, inputText); toast('Saved!', 'success') }}
                    className="text-[10px] text-muted-foreground hover:text-primary flex items-center gap-0.5">
                    <Bookmark className="w-3 h-3" /> Save
                  </button>
                  <button onClick={() => analyzeData(inputText)}
                    className="text-[10px] text-primary flex items-center gap-0.5">
                    <RefreshCw className="w-3 h-3" /> Retry
                  </button>
                </div>
              </div>
            </div>

            {/* AI Analysis */}
            {aiResult && (
              <div className="card-enterprise p-4 animate-fade-up">
                <div className="flex items-center gap-2 mb-2">
                  <Sparkles className="w-3.5 h-3.5 text-[#a78bfa]" />
                  <h3 className="text-xs font-semibold">AI Verification</h3>
                  <span className={`ml-auto text-[10px] px-1.5 py-0.5 rounded-full font-medium ${
                    aiResult.verdict === "LIKELY_TRUE" ? "bg-[#4ADE80]/15 text-[#4ADE80]" :
                    aiResult.verdict === "LIKELY_FALSE" ? "bg-destructive/15 text-destructive" :
                    "bg-accent/15 text-accent"
                  }`}>{aiResult.verdict?.replace(/_/g, " ") || aiResult.credibility}</span>
                </div>
                <p className="text-xs text-muted-foreground leading-relaxed line-clamp-4">{aiResult.analysis || "No analysis available."}</p>
              </div>
            )}

            {/* Feedback */}
            <div className="card-enterprise p-4 animate-fade-up">
              <h3 className="text-xs font-semibold mb-2">Correct prediction?</h3>
              {feedbackSent ? (
                <p className="text-[10px] text-[#4ADE80]">✓ Thanks for the feedback!</p>
              ) : (
                <div className="flex gap-2">
                  <Button variant="outline" size="sm" onClick={() => sendFeedback(true)} className="flex-1 text-xs">
                    <ThumbsUp className="w-3.5 h-3.5 mr-1" /> Yes
                  </Button>
                  <Button variant="outline" size="sm" onClick={() => sendFeedback(false)} className="flex-1 text-xs">
                    <ThumbsDown className="w-3.5 h-3.5 mr-1" /> No
                  </Button>
                </div>
              )}
            </div>

            {/* Share — compact */}
            <div className="card-enterprise p-4 animate-fade-up">
              <h3 className="text-xs font-semibold mb-2 flex items-center gap-1.5"><Share2 className="w-3.5 h-3.5" /> Share</h3>
              <div className="grid grid-cols-2 gap-2">
                <Button variant="outline" size="sm" className="text-[10px]" onClick={() => {
                  const url = result.claim_hash ? `https://fake-news-detector-8djq.onrender.com/claim/${result.claim_hash}` : 'https://fake-news-detector-8djq.onrender.com';
                  navigator.clipboard.writeText(url).then(() => logShare('copy'))
                }}>
                  <Copy className="w-3 h-3 mr-1" /> Copy
                </Button>
                <Button variant="outline" size="sm" className="text-[10px]" onClick={() => {
                  const url = result.claim_hash ? `https://fake-news-detector-8djq.onrender.com/claim/${result.claim_hash}` : 'https://fake-news-detector-8djq.onrender.com';
                  const text = encodeURIComponent(`VERIFAI: ${result.prediction} (${result.confidence.toFixed(0)}%) — ${url}`)
                  window.open(`https://wa.me/?text=${text}`, '_blank')
                  logShare('whatsapp')
                }}>
                  WhatsApp
                </Button>
              </div>
            </div>

            {/* Explainable — collapsible */}
            <div className="card-enterprise overflow-hidden animate-fade-up">
              <button onClick={() => setShowExplain(!showExplain)} className="w-full flex items-center justify-between p-4 text-left">
                <span className="text-xs font-semibold flex items-center gap-1.5"><Search className="w-3.5 h-3.5 text-primary" /> AI Insights</span>
                <ChevronDown className={`w-3.5 h-3.5 text-muted-foreground transition-transform ${showExplain ? 'rotate-180' : ''}`} />
              </button>
              {showExplain && (
                <div className="px-4 pb-4 space-y-2 border-t border-border pt-3">
                  {result.red_flags?.length > 0 && (
                    <div className="space-y-1">
                      {result.red_flags.slice(0, 3).map((f: any, i: number) => (
                        <div key={i} className="flex items-start gap-1.5 text-[10px]">
                          <CircleAlert className="w-3 h-3 text-destructive mt-0.5 shrink-0" />
                          <span className="text-muted-foreground">{typeof f === 'string' ? f : f.description || f.flag}</span>
                        </div>
                      ))}
                    </div>
                  )}
                  <div className="grid grid-cols-2 gap-2">
                    <div className="bg-background rounded-lg p-2 text-center">
                      <div className="text-base font-bold">{(result.real_probability*100).toFixed(0)}%</div>
                      <div className="text-[9px] text-[#4ADE80]">Real</div>
                    </div>
                    <div className="bg-background rounded-lg p-2 text-center">
                      <div className="text-base font-bold">{(result.fake_probability*100).toFixed(0)}%</div>
                      <div className="text-[9px] text-destructive">Fake</div>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Web Sources */}
            {gnewsResult?.articles?.length > 0 && (
              <div className="card-enterprise p-4 animate-fade-up">
                <div className="flex items-center gap-2 mb-2">
                  <Globe className="w-3.5 h-3.5 text-[#38bdf8]" />
                  <h3 className="text-xs font-semibold">Sources</h3>
                  <span className="ml-auto text-[10px] text-muted-foreground">{gnewsResult.articles.length}</span>
                </div>
                <div className="space-y-2">
                  {gnewsResult.articles.slice(0, 3).map((a: any, i: number) => (
                    <a key={i} href={a.url} target="_blank" rel="noopener noreferrer" className="flex items-start gap-2 group">
                      <ExternalLink className="w-3 h-3 text-muted-foreground mt-0.5 shrink-0" />
                      <div className="min-w-0">
                        <p className="text-[11px] font-medium truncate">{a.title}</p>
                        <p className="text-[9px] text-muted-foreground">{a.source?.name}</p>
                      </div>
                    </a>
                  ))}
                </div>
              </div>
            )}

            {/* Fact Check */}
            {factResult && factResult.claims?.length > 0 && (
              <div className="card-enterprise p-4 animate-fade-up">
                <div className="flex items-center gap-2 mb-2">
                  <Search className="w-3.5 h-3.5 text-[#facc15]" />
                  <h3 className="text-xs font-semibold">Fact Check</h3>
                </div>
                {factResult.claims.slice(0, 2).map((c: any, i: number) => (
                  <div key={i} className="bg-background rounded-lg p-2.5 mb-1.5">
                    <p className="text-[10px] font-medium mb-0.5">{c.text}</p>
                    <p className="text-[9px] text-muted-foreground">
                      <span className="text-[#facc15]">{c.claimReview?.[0]?.textualRating || 'Unrated'}</span>
                    </p>
                  </div>
                ))}
              </div>
            )}

            {/* Safe Browsing + Credibility */}
            {safeBrowsing && (
              <div className="card-enterprise p-4 animate-fade-up">
                <div className="flex items-center gap-2 mb-1">
                  <ShieldCheck className="w-3.5 h-3.5 text-[#4ADE80]" />
                  <h3 className="text-xs font-semibold">Safe Browsing</h3>
                  <span className={`ml-auto text-[9px] px-1.5 py-0.5 rounded-full font-medium ${safeBrowsing.safe ? 'bg-[#4ADE80]/15 text-[#4ADE80]' : 'bg-destructive/15 text-destructive'}`}>
                    {safeBrowsing.safe ? 'SAFE' : 'THREATS'}
                  </span>
                </div>
              </div>
            )}

            {/* Export — compact */}
            <div className="card-enterprise p-4 animate-fade-up">
              <Button variant="outline" size="sm" className="w-full text-xs" onClick={exportText}>
                <FileDown className="w-3.5 h-3.5 mr-1.5" /> Export Report
              </Button>
            </div>

            {/* India Threat Scanner */}
            {(() => {
              const txt = inputText.toLowerCase()
              const threats: { type: string; label: string }[] = []
              if (/upi|paytm|phonepe|google\s*pay|bhim|gpay/.test(txt) && /reward|prize|won|cashback/.test(txt))
                threats.push({ type: "upi", label: "UPI Fraud Alert" })
              if (/government|modi|scheme|yojana|aadhaar/.test(txt) && /apply|register|click|link|free/.test(txt))
                threats.push({ type: "govt", label: "Fake Govt Scheme" })
              if (/forward|share|whatsapp|viral|circulating/.test(txt))
                threats.push({ type: "forward", label: "WhatsApp Forward" })

              return threats.length > 0 ? (
                <div className="bg-secondary rounded-xl border border-accent/30 p-4 animate-fade-up">
                  <div className="flex items-center gap-2 mb-2">
                    <ShieldAlert className="w-3.5 h-3.5 text-accent" />
                    <span className="text-xs font-semibold">Threat Scanner</span>
                    <span className="ml-auto text-[9px] px-1.5 py-0.5 rounded-full bg-accent/15 text-accent">{threats.length}</span>
                  </div>
                  <div className="space-y-1.5">
                    {threats.map((t, i) => (
                      <div key={i} className="flex items-center gap-2 bg-background rounded-lg p-2">
                        {t.type === 'upi' ? <Ban className="w-4 h-4 text-destructive" /> : t.type === 'govt' ? <Landmark className="w-4 h-4 text-accent" /> : <MessageCircle className="w-4 h-4 text-[#38bdf8]" />}
                        <span className="text-[10px] font-medium text-accent">{t.label}</span>
                      </div>
                    ))}
                  </div>
                </div>
              ) : null
            })()}
          </div>
        ) : loading ? (
          <div className="space-y-3">
            <div className="bg-secondary rounded-xl border border-border p-4 space-y-3 animate-fade-up">
              <div className="flex items-center gap-3">
                <div className="animate-pulse bg-muted rounded-full w-14 h-14" />
                <div className="space-y-2 flex-1"><div className="animate-pulse bg-muted rounded-lg h-4 w-20" /><div className="animate-pulse bg-muted rounded-lg h-2 w-28" /></div>
              </div>
              <div className="animate-pulse bg-muted rounded-lg h-1.5 w-full" />
              <div className="animate-pulse bg-muted rounded-lg h-1.5 w-4/5" />
            </div>
          </div>
        ) : (
          <div className="bg-background border border-border border-dashed rounded-xl p-6 flex flex-col items-center justify-center text-center min-h-[200px]">
            <ShieldAlert className="w-10 h-10 text-muted mb-3" />
            <h3 className="text-sm font-medium mb-1">No Analysis Yet</h3>
            <p className="text-xs text-muted-foreground max-w-[180px]">
              Submit text, URL, or audio above to see results.
            </p>
          </div>
        )}

        {/* Recent — compact */}
        {recentAnalyses.length > 0 && (
          <div className="bg-secondary border border-border rounded-xl p-4">
            <h3 className="text-xs font-semibold mb-2">This Session</h3>
            <div className="space-y-1.5">
              {recentAnalyses.slice(0, 3).map((r, i) => (
                <div key={i} className="flex items-center gap-2 bg-background rounded-lg px-2 py-1.5">
                  <span className={`text-[9px] font-medium px-1.5 py-0.5 rounded-full ${r.prediction === 'FAKE' ? 'bg-destructive/15 text-destructive' : 'bg-[#4ADE80]/15 text-[#4ADE80]'}`}>{r.prediction}</span>
                  <span className="text-[10px] text-muted-foreground truncate flex-1">{r.preview?.slice(0, 30)}...</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
