import { useEffect, useState } from "react"
import { useParams, Link } from "react-router-dom"
import { ShieldAlert, ShieldCheck, Sparkles, AlertTriangle, ArrowRight, Home, Loader2, ArrowLeft, Download, Share2, Copy, ExternalLink } from "lucide-react"

export function Claim() {
  const { hash } = useParams()
  const [claim, setClaim] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")
  const [copied, setCopied] = useState(false)

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
        // Update document title dynamically
        const verdict = (data.verdict || "").replace(/_/g, " ")
        document.title = `VerifAI: ${verdict} (${data.confidence?.toFixed(0)}% confidence)`
        // Inject JSON-LD structured data for SEO
        const ratingMap: Record<string, {name: string, val: number}> = {
          LIKELY_TRUE: {name: "True", val: 4}, LIKELY_FALSE: {name: "False", val: 1},
          MIXED: {name: "Mixture", val: 3}, UNVERIFIABLE: {name: "Unverifiable", val: 3},
        }
        const r = ratingMap[data.verdict] || ratingMap.UNVERIFIABLE
        const jsonLd = document.createElement("script")
        jsonLd.type = "application/ld+json"
        jsonLd.text = JSON.stringify({
          "@context": "https://schema.org", "@type": "ClaimReview",
          url: `https://fake-news-detector-8djq.onrender.com/claim/${hash}`,
          claimReviewed: (data.claim_text || data.text || "").slice(0, 500),
          author: {"@type": "Organization", name: "VerifAI", url: "https://fake-news-detector-8djq.onrender.com"},
          reviewRating: {"@type": "Rating", ratingValue: r.val, bestRating: 5, worstRating: 1, alternateName: r.name},
          itemReviewed: {"@type": "Claim", name: (data.claim_text || data.text || "").slice(0, 200)},
        })
        document.head.appendChild(jsonLd)
      })
      .catch(err => {
        setError(err.message)
        setLoading(false)
      })
  }, [hash])

  const cardUrl = hash ? `/api/v1/claim/${hash}/card.svg` : ""
  const pageUrl = `https://fake-news-detector-8djq.onrender.com/claim/${hash}`

  const handleCopyLink = () => {
    navigator.clipboard.writeText(pageUrl).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }

  const handleDownloadCard = () => {
    const link = document.createElement("a")
    link.href = cardUrl
    link.download = `verifai-verdict-${hash?.slice(0, 8)}.svg`
    link.click()
  }

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

        {/* Shareable Verdict Card */}
        <div className="card-enterprise p-6 animate-fade-up" style={{ animationDelay: "0.15s" }}>
          <div className="flex items-center gap-2 mb-4">
            <Share2 className="w-5 h-5 text-primary" />
            <h3 className="text-lg font-semibold font-heading">Share This Verdict</h3>
          </div>
          
          {/* Card Preview */}
          <div className="rounded-xl overflow-hidden border border-border mb-4 bg-[#0B0E15]">
            <img src={cardUrl} alt="Verdict card preview" className="w-full" loading="lazy" />
          </div>
          
          {/* Share Actions */}
          <div className="flex flex-wrap gap-2">
            <button onClick={handleCopyLink}
              className="flex-1 min-w-[140px] flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl border border-border bg-secondary/50 text-sm font-medium hover:bg-secondary hover:border-primary/30 transition-all">
              <Copy className="w-4 h-4" /> {copied ? "Copied!" : "Copy Link"}
            </button>
            <button onClick={handleDownloadCard}
              className="flex-1 min-w-[140px] flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl border border-border bg-secondary/50 text-sm font-medium hover:bg-secondary hover:border-primary/30 transition-all">
              <Download className="w-4 h-4" /> Download Card
            </button>
            <a href={`https://wa.me/?text=${encodeURIComponent(`VerifAI Fact Check: ${claim.verdict?.replace(/_/g, " ")} (${claim.confidence?.toFixed(0)}% confidence)\n\n${pageUrl}`)}`}
              target="_blank" rel="noreferrer"
              className="flex-1 min-w-[140px] flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl border border-border bg-secondary/50 text-sm font-medium hover:bg-secondary hover:border-[#25D366]/50 transition-all">
              <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/></svg>
              WhatsApp
            </a>
            <a href={`https://twitter.com/intent/tweet?text=${encodeURIComponent(`Fact check: ${claim.verdict?.replace(/_/g, " ")} (${claim.confidence?.toFixed(0)}% confidence)`)}&url=${encodeURIComponent(pageUrl)}`}
              target="_blank" rel="noreferrer"
              className="flex-1 min-w-[140px] flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl border border-border bg-secondary/50 text-sm font-medium hover:bg-secondary hover:border-foreground/30 transition-all">
              <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>
              Tweet
            </a>
          </div>
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
                    <ExternalLink className="w-4 h-4 text-muted-foreground shrink-0 mt-1 group-hover:text-primary" />
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
