import { FileText, Brain, ShieldCheck } from "lucide-react"

export function HowItWorksSection() {
  return (
    <section id="how-it-works" className="bg-background py-24 px-8 lg:px-16">
      <h2 className="text-foreground text-4xl font-bold mb-4">How it works</h2>
      <p className="text-muted-foreground mb-16">Three steps. Instant verdict.</p>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        
        {/* Card 1 */}
        <div className="bg-secondary border border-border rounded-lg p-6 hover:border-primary/40 transition-colors">
          <FileText className="text-primary w-12 h-12 mb-6" strokeWidth={1.5} />
          <div className="text-primary text-sm font-semibold mb-2">01</div>
          <h3 className="text-foreground text-xl font-semibold mb-3">Paste article or URL</h3>
          <p className="text-muted-foreground">
            Drop in any news article, social post, or URL. Works with text in any language.
          </p>
        </div>

        {/* Card 2 */}
        <div className="bg-secondary border border-border rounded-lg p-6 hover:border-primary/40 transition-colors">
          <Brain className="text-primary w-12 h-12 mb-6" strokeWidth={1.5} />
          <div className="text-primary text-sm font-semibold mb-2">02</div>
          <h3 className="text-foreground text-xl font-semibold mb-3">AI ensemble analyzes</h3>
          <p className="text-muted-foreground">
            5 ML models run in parallel — Random Forest, SVM, Gradient Boosting, Logistic Regression, Naive Bayes.
          </p>
        </div>

        {/* Card 3 */}
        <div className="bg-secondary border border-border rounded-lg p-6 hover:border-primary/40 transition-colors">
          <ShieldCheck className="text-primary w-12 h-12 mb-6" strokeWidth={1.5} />
          <div className="text-primary text-sm font-semibold mb-2">03</div>
          <h3 className="text-foreground text-xl font-semibold mb-3">Get instant verdict</h3>
          <p className="text-muted-foreground">
            Real-time confidence score, source cross-check via GNews API, and semantic verification via Gemini AI.
          </p>
        </div>

      </div>
    </section>
  )
}
