import { Link } from "react-router-dom"

export function Footer() {
  return (
    <footer className="bg-[#0b0e15] border-t border-white/5 text-white">
      <div className="max-w-5xl mx-auto px-6 py-14">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-10 mb-12">
          {/* Brand */}
          <div className="col-span-2 md:col-span-1">
            <div className="text-xl font-heading font-bold mb-3">
              VERIF<span className="text-primary">AI</span>
            </div>
            <p className="text-white/40 text-sm leading-relaxed">
              AI-powered misinformation detection platform. Fight fake news with machine learning.
            </p>
          </div>

          {/* Platform */}
          <div>
            <h4 className="text-xs font-mono font-semibold uppercase tracking-widest text-white/60 mb-4">Platform</h4>
            <div className="space-y-2.5">
              <Link to="/about" className="block text-sm text-white/40 hover:text-white transition-colors">About</Link>
              <a href="/#how-it-works" className="block text-sm text-white/40 hover:text-white transition-colors">How It Works</a>
              <a href="/#accuracy" className="block text-sm text-white/40 hover:text-white transition-colors">Features</a>
              <Link to="/privacy" className="block text-sm text-white/40 hover:text-white transition-colors">Privacy</Link>
            </div>
          </div>

          {/* Resources */}
          <div>
            <h4 className="text-xs font-mono font-semibold uppercase tracking-widest text-white/60 mb-4">Resources</h4>
            <div className="space-y-2.5">
              <a href="https://github.com/imkoushal/fake-news-detector-ai" target="_blank" rel="noreferrer" className="block text-sm text-white/40 hover:text-white transition-colors">GitHub</a>
              <a href="https://github.com/imkoushal/fake-news-detector-ai/issues" target="_blank" rel="noreferrer" className="block text-sm text-white/40 hover:text-white transition-colors">Report Bug</a>
              <a href="https://razorpay.me/@koushalkishorray" target="_blank" rel="noreferrer" className="block text-sm text-amber-400/60 hover:text-amber-400 transition-colors">☕ Support VerifAI</a>
            </div>
          </div>

          {/* Stack */}
          <div>
            <h4 className="text-xs font-mono font-semibold uppercase tracking-widest text-white/60 mb-4">Tech Stack</h4>
            <div className="space-y-2.5">
              <span className="block text-sm text-white/40">React + Vite</span>
              <span className="block text-sm text-white/40">FastAPI + PyTorch</span>
              <span className="block text-sm text-white/40">5-Model Ensemble</span>
            </div>
          </div>
        </div>

        {/* Bottom bar */}
        <div className="border-t border-white/5 pt-6 flex flex-wrap justify-between items-center gap-3">
          <p className="text-xs text-white/30">© {new Date().getFullYear()} VERIFAI — Built by <a href="https://github.com/imkoushal" target="_blank" rel="noreferrer" className="text-primary/70 hover:text-primary transition-colors">Koushal</a></p>
          <p className="text-xs text-white/30 font-mono">v2.0 · Enterprise Edition</p>
        </div>
      </div>
    </footer>
  )
}
