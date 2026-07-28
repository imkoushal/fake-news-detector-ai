import { Shield, Zap, Brain, Globe, Lock, Users, ArrowRight, Heart, ExternalLink } from "lucide-react"
import { Link } from "react-router-dom"
import { Button } from "../components/ui/button"

const features = [
  {
    icon: Brain,
    title: "AI-Powered Analysis",
    desc: "Our multi-model ensemble analyzes content across multiple dimensions to detect misinformation with high accuracy.",
  },
  {
    icon: Zap,
    title: "Instant Results",
    desc: "Get comprehensive fact-check results in seconds. Paste any article, URL, or audio and receive a detailed verdict.",
  },
  {
    icon: Globe,
    title: "Cross-Reference Verification",
    desc: "Every analysis is cross-referenced against trusted news sources and fact-checking databases for reliability.",
  },
  {
    icon: Shield,
    title: "Transparent Scoring",
    desc: "See exactly how our system reaches its verdict with clear confidence scores and source breakdowns.",
  },
  {
    icon: Lock,
    title: "Privacy First",
    desc: "Your data stays private. We don't store article content after analysis and never share your information.",
  },
  {
    icon: Users,
    title: "Built for Everyone",
    desc: "Whether you're a journalist, researcher, student, or curious reader — VerifAI makes fact-checking accessible.",
  },
]

const stats = [
  { value: "157K+", label: "Training Articles" },
  { value: "94.5%", label: "Accuracy Rate" },
  { value: "5", label: "ML Models" },
  { value: "<5s", label: "Avg Response" },
]

export function AboutPage() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="max-w-5xl mx-auto px-4 md:px-8 pt-28 pb-20">

        {/* Hero */}
        <div className="text-center mb-20">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-primary/10 border border-primary/20 text-primary text-sm font-medium mb-6">
            <Shield className="w-4 h-4" />
            Fighting Misinformation with AI
          </div>
          <h1 className="text-4xl md:text-5xl font-bold tracking-tight mb-5 font-heading">
            About <span className="text-primary">VERIF</span>AI
          </h1>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto leading-relaxed">
            VerifAI is an AI-powered misinformation detection platform that helps you verify the credibility of news articles, social media posts, and online content in seconds.
          </p>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-20">
          {stats.map(s => (
            <div key={s.label} className="bg-secondary/50 border border-border rounded-2xl p-6 text-center hover:border-primary/30 transition-colors">
              <p className="text-3xl font-bold text-primary mb-1">{s.value}</p>
              <p className="text-sm text-muted-foreground">{s.label}</p>
            </div>
          ))}
        </div>

        {/* Mission */}
        <div className="bg-gradient-to-br from-primary/5 via-secondary/50 to-secondary/30 border border-border rounded-2xl p-8 md:p-12 mb-20">
          <h2 className="text-2xl font-bold mb-4 font-heading">Our Mission</h2>
          <p className="text-muted-foreground leading-relaxed text-[15px] mb-4">
            In an era of information overload, distinguishing fact from fiction has become increasingly challenging. VerifAI was built to empower individuals with the tools they need to make informed decisions about the content they consume and share.
          </p>
          <p className="text-muted-foreground leading-relaxed text-[15px]">
            We combine cutting-edge machine learning with real-time web verification to provide transparent, explainable fact-checking that anyone can understand and trust.
          </p>
        </div>

        {/* Features */}
        <div className="mb-20">
          <h2 className="text-2xl font-bold text-center mb-10 font-heading">What Makes VerifAI Different</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {features.map(f => (
              <div key={f.title} className="bg-secondary/30 border border-border rounded-2xl p-6 hover:border-primary/30 transition-all group">
                <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center mb-4 group-hover:bg-primary/20 transition-colors">
                  <f.icon className="w-5 h-5 text-primary" />
                </div>
                <h3 className="text-[15px] font-semibold mb-2">{f.title}</h3>
                <p className="text-sm text-muted-foreground leading-relaxed">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>

        {/* How It Works (simplified, user-friendly) */}
        <div className="mb-20">
          <h2 className="text-2xl font-bold text-center mb-10 font-heading">How It Works</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[
              { step: "01", title: "Submit Content", desc: "Paste an article, enter a URL, or upload audio. VerifAI accepts multiple input formats." },
              { step: "02", title: "AI Analysis", desc: "Our system runs the content through multiple AI models and cross-references trusted sources." },
              { step: "03", title: "Get Your Verdict", desc: "Receive a detailed breakdown with a confidence score, source verification, and actionable insights." },
            ].map(s => (
              <div key={s.step} className="relative bg-secondary/30 border border-border rounded-2xl p-6 text-center">
                <span className="text-5xl font-bold text-primary/10 absolute top-4 right-5 font-heading">{s.step}</span>
                <div className="relative z-10">
                  <h3 className="text-lg font-semibold mb-2 mt-4">{s.title}</h3>
                  <p className="text-sm text-muted-foreground leading-relaxed">{s.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Open Source + Links */}
        <div className="bg-secondary/30 border border-border rounded-2xl p-8 md:p-10 mb-20">
          <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
            <div>
              <h2 className="text-xl font-bold mb-2 font-heading">Open Source & Transparent</h2>
              <p className="text-sm text-muted-foreground leading-relaxed max-w-lg">
                VerifAI is open source. Our code, models, and methodology are publicly available for anyone to inspect, contribute to, or learn from.
              </p>
            </div>
            <a
              href="https://github.com/imkoushal/fake-news-detector-ai"
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-foreground text-background text-sm font-medium hover:opacity-90 transition-opacity shrink-0"
            >
              View on GitHub
              <ExternalLink className="w-4 h-4" />
            </a>
          </div>
        </div>

        {/* CTA */}
        <div className="text-center">
          <h2 className="text-2xl font-bold mb-3 font-heading">Ready to Verify?</h2>
          <p className="text-muted-foreground mb-6">Start fact-checking content in seconds.</p>
          <div className="flex items-center justify-center gap-4">
            <Link to="/analytics">
              <Button size="lg" className="px-8 gap-2">
                Start Analyzing
                <ArrowRight className="w-4 h-4" />
              </Button>
            </Link>
            <a href="https://razorpay.me/@koushalkishorray" target="_blank" rel="noreferrer">
              <Button variant="outline" size="lg" className="px-6 gap-2 text-amber-400 border-amber-400/30 hover:bg-amber-400/10">
                <Heart className="w-4 h-4" />
                Support Us
              </Button>
            </a>
          </div>
        </div>

      </div>
    </div>
  )
}
