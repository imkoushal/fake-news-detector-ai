import React, { Suspense } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

const Spline = React.lazy(() => import('@splinetool/react-spline'))

export function HeroSection() {
  const { user, setShowAuthModal } = useAuth();
  const navigate = useNavigate();

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

      {/* Dark overlay */}
      <div className="absolute inset-0 bg-black/40 z-[1] pointer-events-none" />

      {/* Content */}
      <div className="relative z-10 pointer-events-none w-full max-w-[90%] sm:max-w-md lg:max-w-2xl px-6 md:px-10 pb-10 md:pb-14 pt-32 mt-auto">
        
        <span 
          className="opacity-0 animate-fade-up bg-primary/10 text-primary border border-primary/30 text-xs tracking-widest px-3 py-1 rounded-full mb-4 inline-block"
          style={{ animationDelay: "0.1s" }}
        >
          AI-POWERED MISINFORMATION DETECTION
        </span>

        <h1 
          className="opacity-0 animate-fade-up text-[clamp(3rem,8vw,6rem)] font-bold leading-[1.05] tracking-[-0.05em] uppercase mb-2 md:mb-4"
          style={{ animationDelay: "0.2s" }}
        >
          <span className="text-foreground">DETECT</span>
          <span className="text-primary"> FAKE</span>
          <span className="text-foreground"> NEWS.</span>
        </h1>

        <p 
          className="opacity-0 animate-fade-up text-foreground/80 text-[clamp(1.125rem,2.5vw,1.875rem)] font-light mb-3 md:mb-6"
          style={{ animationDelay: "0.4s" }}
        >
          Real-time verification. Zero misinformation.
        </p>

        <p 
          className="opacity-0 animate-fade-up text-muted-foreground text-[clamp(0.875rem,1.5vw,1.125rem)] font-light mb-4 md:mb-8 max-w-lg"
          style={{ animationDelay: "0.55s" }}
        >
          Paste any article or URL. Our 5-model AI ensemble — trained on 157,000+ articles — cross-references live sources, detects manipulation patterns, and tells you exactly why something is fake. In seconds.
        </p>

        <div 
          className="opacity-0 animate-fade-up flex flex-wrap gap-3 font-bold pointer-events-auto"
          style={{ animationDelay: "0.7s" }}
        >
          <button 
            onClick={() => user ? navigate('/dashboard') : setShowAuthModal(true)}
            className="bg-primary text-primary-foreground px-6 py-3 md:px-8 md:py-4 text-sm rounded-sm hover:brightness-110 transition-all active:scale-[0.97]"
          >
            {user ? "Go to Dashboard →" : "Analyze Article →"}
          </button>
          <a 
            href="https://github.com/imkoushal/fake-news-detector-ai" 
            target="_blank" 
            rel="noopener noreferrer"
            className="bg-white/10 text-foreground border border-white/20 px-6 py-3 md:px-8 md:py-4 text-sm rounded-sm hover:bg-white/20 transition-all active:scale-[0.97]"
          >
            View on GitHub
          </a>
        </div>

        <div 
          className="opacity-0 animate-fade-up flex flex-row gap-6 text-xs text-muted-foreground/70 font-light mt-4 md:mt-6"
          style={{ animationDelay: "0.85s" }}
        >
          <span>96.46% accuracy</span>
          <span>·</span>
          <span>157K+ articles trained</span>
          <span>·</span>
          <span>India threat detection</span>
        </div>

      </div>
    </section>
  )
}
