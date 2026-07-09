import { useEffect, useState } from "react"
import { useParams, Link } from "react-router-dom"
import { ShieldAlert, ShieldCheck, Sparkles, AlertTriangle, ArrowRight, Home, Loader2, ArrowLeft } from "lucide-react"

export function Claim() {
  const { hash } = useParams()
  const [claim, setClaim] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")

  useEffect(() => {
    if (!hash) return
    
    fetch(`/api/v1/claim/${hash}`)
      .then(res => {
        if (!res.ok) throw new Error("Claim not found")
        return res.json()
      })
      .then(data => {
        setClaim(data)
        setLoading(false)
      })
      .catch(err => {
        setError(err.message)
        setLoading(false)
      })
  }, [hash])

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex flex-col items-center justify-center p-6">
        <Loader2 className="w-8 h-8 animate-spin text-primary mb-4" />
        <p className="text-muted-foreground font-medium">Loading verification report...</p>
      </div>
    )
  }

  if (error || !claim) {
    return (
      <div className="min-h-screen bg-background flex flex-col items-center justify-center p-6 text-center">
        <AlertTriangle className="w-12 h-12 text-destructive mb-4" />
        <h1 className="text-2xl font-bold font-heading mb-2">Claim Not Found</h1>
        <p className="text-muted-foreground mb-6 max-w-md">We couldn't find a public verification report for this claim. It may have expired or never existed.</p>
        <Link to="/" className="btn-gradient px-6 py-2 rounded-lg font-medium inline-flex items-center gap-2">
          <Home className="w-4 h-4" /> Go to Homepage
        </Link>
      </div>
    )
  }

  const isFake = claim.verdict === "LIKELY_FALSE"
  const isTrue = claim.verdict === "LIKELY_TRUE"

  return (
    <div className="min-h-screen bg-background flex flex-col">
      {/* Simple Header */}
      <header className="h-16 border-b border-border bg-[#0b0e15] flex items-center px-6">
        <Link to="/" className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center">
            <span className="text-white text-sm font-bold font-heading">V</span>
          </div>
          <span className="text-white text-lg font-bold font-heading tracking-tight">VERIF<span className="text-primary">AI</span></span>
        </Link>
      </header>

      <main className="flex-1 max-w-3xl w-full mx-auto p-4 md:p-8 space-y-6">
        {/* Back Link */}
        <Link to="/" className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-primary transition-colors">
          <ArrowLeft className="w-4 h-4" /> Back to scanner
        </Link>

        {/* Hero Section */}
        <div className="text-center space-y-4 py-6">
          <div className="inline-flex items-center justify-center p-3 rounded-2xl bg-secondary/50 border border-border/50 mb-2 shadow-sm">
            {isFake ? <ShieldAlert className="w-8 h-8 text-destructive" /> : 
             isTrue ? <ShieldCheck className="w-8 h-8 text-[#4ADE80]" /> : 
             <Sparkles className="w-8 h-8 text-accent" />}
          </div>
          <h1 className="text-3xl md:text-4xl font-extrabold font-heading tracking-tight leading-tight">
            {isFake ? "This claim is likely false." : 
             isTrue ? "This claim is likely true." : 
             "This claim has mixed evidence."}
          </h1>
          <p className="text-muted-foreground max-w-xl mx-auto">
            Verified by VerifAI's multi-layered fact-checking engine with {claim.confidence?.toFixed(1) || "???"}% confidence.
          </p>
        </div>

        {/* The Claim */}
        <div className="card-enterprise p-6 relative overflow-hidden group border-border hover:border-primary/50 transition-colors">
          <div className="absolute top-0 left-0 w-1 h-full bg-primary" />
          <h3 className="text-xs font-mono font-semibold text-muted-foreground uppercase tracking-widest mb-3">The Claim</h3>
          <p className="text-lg md:text-xl font-medium leading-relaxed italic text-foreground/90">
            "{claim.claim_text || claim.text || "Original text not provided."}"
          </p>
        </div>

        {/* AI Analysis */}
        <div className="card-enterprise p-6 animate-fade-up" style={{ animationDelay: "0.1s" }}>
          <div className="flex items-center gap-2 mb-4">
            <Sparkles className="w-5 h-5 text-[#a78bfa]" />
            <h3 className="text-lg font-semibold font-heading">AI Analysis</h3>
          </div>
          <p className="text-muted-foreground leading-relaxed">
            {claim.analysis || claim.aiResult?.analysis || "No detailed analysis available for this claim."}
          </p>
        </div>

        {/* Evidence Sources */}
        {claim.web?.articles?.length > 0 && (
          <div className="card-enterprise p-6 animate-fade-up" style={{ animationDelay: "0.2s" }}>
            <h3 className="text-lg font-semibold font-heading mb-4">Evidence & Sources</h3>
            <div className="space-y-4">
              {claim.web.articles.slice(0, 3).map((article: any, i: number) => (
                <a key={i} href={article.url} target="_blank" rel="noreferrer" 
                  className="block p-4 rounded-xl border border-border bg-secondary/20 hover:bg-secondary/40 hover:border-primary/30 transition-all group">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <h4 className="font-medium text-foreground mb-1 group-hover:text-primary transition-colors">{article.title}</h4>
                      <div className="flex items-center gap-2 text-xs text-muted-foreground">
                        <span className="px-2 py-0.5 rounded-full bg-background border border-border font-medium text-foreground/70">{article.source}</span>
                        <span>{article.publishedAt ? new Date(article.publishedAt).toLocaleDateString() : 'Recent'}</span>
                      </div>
                    </div>
                  </div>
                </a>
              ))}
            </div>
          </div>
        )}

        {/* CTA */}
        <div className="mt-12 text-center p-8 bg-gradient-to-br from-primary/10 via-background to-secondary/30 rounded-2xl border border-primary/20">
          <h2 className="text-2xl font-bold font-heading mb-3">Received a suspicious forward?</h2>
          <p className="text-muted-foreground mb-6 max-w-md mx-auto">Verify any news article, WhatsApp forward, or social media post in seconds.</p>
          <Link to="/" className="btn-gradient px-8 py-3 rounded-xl font-semibold inline-flex items-center gap-2 hover:scale-105 transition-transform shadow-lg shadow-primary/25">
            Try VerifAI For Free <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </main>

      <footer className="py-8 text-center text-sm text-muted-foreground border-t border-border mt-auto">
        <p>Verified by VerifAI. Fight fake news with machine learning.</p>
      </footer>
    </div>
  )
}
