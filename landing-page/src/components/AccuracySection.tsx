import { useAuth } from "../context/AuthContext"
import { Brain, ShieldCheck, Radar, Layers, BarChart3, Zap } from "lucide-react"

const features = [
  { icon: Brain, title: "5-Model Ensemble", desc: "Random Forest, SVM, Gradient Boosting, Logistic Regression, and Naive Bayes working in parallel." },
  { icon: ShieldCheck, title: "Source Verification", desc: "Google Safe Browsing + domain credibility scoring cross-referenced in real time." },
  { icon: Radar, title: "Threat Scanner", desc: "India-specific detection for UPI scams, government impersonation, and medical misinformation." },
  { icon: Layers, title: "Batch Processing", desc: "Upload CSV files with up to 500 articles. Get bulk analysis with downloadable results." },
  { icon: BarChart3, title: "Live Analytics", desc: "Activity trends, topic breakdowns, date-range filtering, and exportable reports." },
  { icon: Zap, title: "Instant Results", desc: "Sub-2-second analysis with confidence scores, red flags, and explainable AI reasoning." },
]

export function AccuracySection() {
  const { setShowAuthModal } = useAuth()

  return (
    <section id="accuracy" className="bg-hero-bg py-24 px-6 lg:px-16">
      <div className="max-w-5xl mx-auto">
        {/* Header */}
        <div className="text-center mb-16">
          <p className="text-xs font-mono font-semibold text-primary tracking-widest uppercase mb-3">Platform Features</p>
          <h2 className="text-foreground text-4xl md:text-5xl font-heading font-extrabold tracking-tight mb-4">
            Everything you need to <span className="text-gradient-red">fight misinformation</span>
          </h2>
          <p className="text-muted-foreground text-lg max-w-xl mx-auto">
            Enterprise-grade verification tools powered by cutting-edge machine learning.
          </p>
        </div>

        {/* Feature grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5 mb-16 stagger-children">
          {features.map((f, i) => (
            <div key={i} className="card-enterprise p-6 group hover-lift fade-up-stagger">
              <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center mb-4 group-hover:bg-primary/20 transition-colors">
                <f.icon className="w-5 h-5 text-primary" strokeWidth={1.5} />
              </div>
              <h3 className="text-foreground font-heading font-bold text-lg mb-2">{f.title}</h3>
              <p className="text-muted-foreground text-sm leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </div>

        {/* CTA */}
        <div className="card-enterprise p-10 text-center relative overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-r from-primary/5 via-transparent to-accent/5 pointer-events-none" />
          <div className="relative">
            <h3 className="text-3xl md:text-4xl font-heading font-extrabold text-foreground mb-3">
              Ready to verify?
            </h3>
            <p className="text-muted-foreground text-lg mb-6 max-w-md mx-auto">
              Join thousands of users fighting misinformation with AI-powered analysis.
            </p>
            <button onClick={() => setShowAuthModal(true)}
              className="btn-gradient rounded-full px-10 py-4 text-sm font-semibold">
              Get Started — It's Free
            </button>
            <p className="text-[11px] text-muted-foreground/50 font-mono mt-4">
              No credit card required · Setup in 30 seconds
            </p>
          </div>
        </div>
      </div>
    </section>
  )
}
