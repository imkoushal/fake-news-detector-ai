import React, { Suspense } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { ArrowRight } from 'lucide-react'

const Spline = React.lazy(() => import('@splinetool/react-spline'))

export function HeroSection() {
  const { user, setShowAuthModal } = useAuth()
  const navigate = useNavigate()

  return (
    <section className="relative min-h-screen flex flex-col bg-hero-bg overflow-hidden">
      
      {/* 3D Spline Background */}
      <div className="absolute inset-0 pointer-events-none">
        <Suspense fallback={<div className="absolute inset-0 bg-hero-bg" />}>
          <Spline 
            scene="https://prod.spline.design/Slk6b8kz3LRlKiyk/scene.splinecode" 
            className="w-full h-full pointer-events-none"
          />
        </Suspense>
      </div>

      {/* Gradient overlays */}
      <div className="absolute inset-0 bg-gradient-to-b from-hero-bg/30 via-transparent to-hero-bg z-[1] pointer-events-none" />
      <div className="absolute inset-0 bg-black/30 z-[1] pointer-events-none" />

      {/* Content */}
      <div className="relative z-10 pointer-events-none w-full max-w-5xl mx-auto px-6 md:px-10 pb-16 md:pb-24 pt-36 mt-auto">
        
        {/* Pill badge */}
        <div 
          className="opacity-0 animate-fade-up inline-flex items-center gap-2 bg-primary/10 border border-primary/20 rounded-full px-4 py-1.5 mb-6"
          style={{ animationDelay: "0.1s" }}>
          <span className="w-2 h-2 rounded-full bg-primary animate-pulse" />
          <span className="text-xs font-mono font-medium text-primary tracking-wide">Trusted by 1,000+ users</span>
        </div>

        {/* Headline */}
        <h1 
          className="opacity-0 animate-fade-up mb-6"
          style={{ animationDelay: "0.2s" }}>
          <span className="block text-foreground text-[clamp(2.5rem,7vw,5rem)] font-heading font-extrabold leading-[1.05] tracking-[-0.03em]">
            AI-Powered Verification
          </span>
          <span className="block text-[clamp(2.5rem,7vw,5rem)] font-heading font-extrabold leading-[1.05] tracking-[-0.03em]">
            for the <span className="text-gradient-red">Modern Internet</span>
          </span>
        </h1>

        {/* Subtitle */}
        <p 
          className="opacity-0 animate-fade-up text-muted-foreground text-[clamp(1rem,2vw,1.25rem)] font-body max-w-2xl mb-8 leading-relaxed"
          style={{ animationDelay: "0.4s" }}>
          Paste any article, URL, or audio. Our 5-model AI ensemble — trained on 157,000+ articles — cross-references live sources and detects manipulation patterns in seconds.
        </p>

        {/* CTAs */}
        <div 
          className="opacity-0 animate-fade-up flex flex-wrap gap-4 pointer-events-auto mb-6"
          style={{ animationDelay: "0.6s" }}>
          <button 
            onClick={() => user ? navigate('/dashboard') : setShowAuthModal(true)}
            className="btn-gradient rounded-full px-8 py-4 text-sm font-semibold flex items-center gap-2 group">
            {user ? "Open Dashboard" : "Start Analyzing — Free"}
            <ArrowRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />
          </button>
          <a 
            href="https://github.com/imkoushal/fake-news-detector-ai" 
            target="_blank" 
            rel="noopener noreferrer"
            className="flex items-center gap-2 bg-white/8 text-foreground border border-white/15 px-8 py-4 text-sm font-medium rounded-full hover:bg-white/15 transition-all">
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/></svg>
            View on GitHub
          </a>
        </div>

        {/* Sub-details */}
        <p 
          className="opacity-0 animate-fade-up text-[11px] text-muted-foreground/50 font-mono"
          style={{ animationDelay: "0.75s" }}>
          No credit card required · 5-model ensemble · 96.46% accuracy · India threat detection
        </p>
      </div>

      {/* Stats bar */}
      <div className="relative z-10 border-t border-white/10 bg-hero-bg/80 backdrop-blur-sm">
        <div className="max-w-5xl mx-auto px-6 py-6 grid grid-cols-2 md:grid-cols-4 gap-6">
          {[
            { value: "5", label: "AI Models" },
            { value: "4", label: "Verification Sources" },
            { value: "<2s", label: "Analysis Time" },
            { value: "96.46%", label: "Accuracy" },
          ].map((s, i) => (
            <div key={i} className="text-center">
              <div className="text-2xl md:text-3xl font-heading font-bold text-foreground">{s.value}</div>
              <div className="text-xs text-muted-foreground font-mono mt-1">{s.label}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
