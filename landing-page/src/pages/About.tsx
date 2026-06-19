import { ArrowRight } from "lucide-react"
import { Link } from "react-router-dom"
import { Button } from "../components/ui/button"

const pipeline = [
  { step: 1, title: "Input", desc: "Paste article text, URL, or audio" },
  { step: 2, title: "Preprocessing", desc: "TF-IDF vectorization + cleaning" },
  { step: 3, title: "ML Ensemble", desc: "5 models vote independently" },
  { step: 4, title: "AI Analysis", desc: "LLM credibility verification" },
  { step: 5, title: "Web Search", desc: "GNews + fact-check cross-reference" },
  { step: 6, title: "Verdict", desc: "Final hybrid confidence score" },
]

const models = [
  { name: "Logistic Regression", desc: "Fast baseline classifier with high interpretability" },
  { name: "Random Forest", desc: "Ensemble tree model for non-linear patterns" },
  { name: "SGD Classifier", desc: "Scalable gradient descent for large datasets" },
  { name: "Support Vector Classifier", desc: "Margin-based classifier for text" },
  { name: "LightGBM", desc: "Gradient boosting with fast training speed" },
]

export function AboutPage() {
  return (
    <div className="min-h-screen bg-background pt-28 px-4 md:px-12 lg:px-20 text-foreground pb-20">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="text-center mb-16">
          <h1 className="text-4xl font-bold tracking-tight mb-3">
            About <span className="text-primary">VERIFAI</span>
          </h1>
          <p className="text-muted-foreground max-w-lg mx-auto">
            Combating misinformation with transparent, multi-layered AI analysis trained on 105,000+ articles.
          </p>
        </div>

        {/* Pipeline */}
        <div className="mb-16">
          <h2 className="text-xl font-bold mb-8 text-center">Forensic Processing Pipeline</h2>
          <div className="flex flex-wrap items-center justify-center gap-2">
            {pipeline.map((s, i) => (
              <div key={s.step} className="flex items-center gap-2">
                <div className="bg-secondary border border-border rounded-xl p-4 text-center min-w-[130px]">
                  <div className="w-8 h-8 rounded-full bg-primary/20 text-primary text-sm font-bold flex items-center justify-center mx-auto mb-2">{s.step}</div>
                  <h4 className="text-sm font-semibold mb-1">{s.title}</h4>
                  <p className="text-[11px] text-muted-foreground">{s.desc}</p>
                </div>
                {i < pipeline.length - 1 && <ArrowRight className="w-4 h-4 text-muted-foreground shrink-0 hidden md:block" />}
              </div>
            ))}
          </div>
        </div>

        {/* Model Details */}
        <div className="mb-16">
          <h2 className="text-xl font-bold mb-6 text-center">Model Architecture</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {models.map(m => (
              <div key={m.name} className="bg-secondary border border-border rounded-xl p-5 text-center hover:border-primary/40 transition-colors">
                <h4 className="text-sm font-semibold mb-1">{m.name}</h4>
                <p className="text-xs text-muted-foreground">{m.desc}</p>
              </div>
            ))}
            <div className="bg-primary/10 border border-primary/30 rounded-xl p-5 text-center">
              <h4 className="text-sm font-semibold text-primary mb-1">VotingClassifier</h4>
              <p className="text-xs text-muted-foreground">Soft-voting ensemble combining all 5 models</p>
            </div>
          </div>
        </div>

        {/* How to Use */}
        <div className="mb-16">
          <h2 className="text-xl font-bold mb-6 text-center">How to Use</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { n: 1, t: "Navigate to the Analyze page" },
              { n: 2, t: "Paste text, URL, or upload audio" },
              { n: 3, t: "Click Analyze and wait for results" },
              { n: 4, t: "Review the multi-layer breakdown" },
            ].map(s => (
              <div key={s.n} className="bg-secondary border border-border rounded-xl p-4 text-center">
                <div className="w-7 h-7 rounded-full bg-primary/20 text-primary text-xs font-bold flex items-center justify-center mx-auto mb-2">{s.n}</div>
                <p className="text-xs text-muted-foreground">{s.t}</p>
              </div>
            ))}
          </div>
        </div>

        {/* CTA */}
        <div className="text-center">
          <Link to="/dashboard">
            <Button size="lg" className="px-8">Start Analyzing →</Button>
          </Link>
        </div>
      </div>
    </div>
  )
}
