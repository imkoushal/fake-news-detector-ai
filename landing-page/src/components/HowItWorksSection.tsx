import { FileText, Brain, ShieldCheck } from "lucide-react"

const steps = [
  {
    num: "01",
    icon: FileText,
    title: "Paste or Upload",
    desc: "Submit any news article, social media post, URL, or audio file. Works with text in any language — auto-translates non-English content.",
    color: "from-primary/20 to-primary/5",
  },
  {
    num: "02",
    icon: Brain,
    title: "AI Analyzes",
    desc: "5-model ML ensemble (Random Forest, SVM, Gradient Boosting, LR, Naive Bayes) runs in parallel. Cross-referenced with 4 verification sources.",
    color: "from-accent/20 to-accent/5",
  },
  {
    num: "03",
    icon: ShieldCheck,
    title: "Get Verdict",
    desc: "Instant confidence score, source credibility check, red flag analysis, India-specific threat scanning, and shareable verification report.",
    color: "from-[#4ADE80]/20 to-[#4ADE80]/5",
  },
]

export function HowItWorksSection() {
  return (
    <section id="how-it-works" className="bg-background py-24 px-6 lg:px-16">
      <div className="max-w-5xl mx-auto">
        {/* Header */}
        <div className="text-center mb-16">
          <p className="text-xs font-mono font-semibold text-primary tracking-widest uppercase mb-3">How It Works</p>
          <h2 className="text-foreground text-4xl md:text-5xl font-heading font-extrabold tracking-tight mb-4">
            Three steps to <span className="text-gradient-red">truth</span>
          </h2>
          <p className="text-muted-foreground text-lg max-w-xl mx-auto">
            From paste to verdict in under 2 seconds. No expertise required.
          </p>
        </div>

        {/* Steps */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {steps.map((step, i) => (
            <div key={i} className="card-enterprise p-7 group relative overflow-hidden">
              {/* Background number */}
              <div className="absolute -top-4 -right-2 text-[120px] font-heading font-extrabold text-foreground/[0.03] leading-none select-none pointer-events-none">
                {step.num}
              </div>
              
              {/* Icon */}
              <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${step.color} flex items-center justify-center mb-5`}>
                <step.icon className="w-6 h-6 text-foreground" strokeWidth={1.5} />
              </div>
              
              {/* Number badge */}
              <div className="inline-flex items-center gap-1.5 text-primary text-xs font-mono font-bold mb-3">
                <span className="w-6 h-px bg-primary/40" />
                STEP {step.num}
              </div>
              
              {/* Title + desc */}
              <h3 className="text-foreground text-xl font-heading font-bold mb-3">{step.title}</h3>
              <p className="text-muted-foreground text-sm leading-relaxed">{step.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
