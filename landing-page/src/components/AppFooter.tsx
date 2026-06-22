import { Link } from "react-router-dom"

export function AppFooter() {
  return (
    <footer className="border-t border-border bg-secondary/50 mt-auto">
      <div className="max-w-6xl mx-auto px-4 md:px-12 py-8">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6 mb-6">
          <div>
            <h4 className="text-xs font-semibold text-foreground uppercase tracking-wider mb-3">Platform</h4>
            <div className="space-y-2">
              <Link to="/dashboard" className="block text-xs text-muted-foreground hover:text-foreground transition-colors">Dashboard</Link>
              <Link to="/batch" className="block text-xs text-muted-foreground hover:text-foreground transition-colors">Batch Analysis</Link>
              <Link to="/analytics" className="block text-xs text-muted-foreground hover:text-foreground transition-colors">Analytics</Link>
            </div>
          </div>
          <div>
            <h4 className="text-xs font-semibold text-foreground uppercase tracking-wider mb-3">Data</h4>
            <div className="space-y-2">
              <Link to="/history" className="block text-xs text-muted-foreground hover:text-foreground transition-colors">History</Link>
              <Link to="/settings" className="block text-xs text-muted-foreground hover:text-foreground transition-colors">Settings</Link>
            </div>
          </div>
          <div>
            <h4 className="text-xs font-semibold text-foreground uppercase tracking-wider mb-3">Learn</h4>
            <div className="space-y-2">
              <Link to="/about" className="block text-xs text-muted-foreground hover:text-foreground transition-colors">About</Link>
              <a href="https://github.com/imkoushal/fake-news-detector-ai" target="_blank" rel="noreferrer" className="block text-xs text-muted-foreground hover:text-foreground transition-colors">GitHub</a>
            </div>
          </div>
          <div>
            <h4 className="text-xs font-semibold text-foreground uppercase tracking-wider mb-3">Stack</h4>
            <div className="space-y-2">
              <span className="block text-xs text-muted-foreground">React + Vite</span>
              <span className="block text-xs text-muted-foreground">FastAPI + PyTorch</span>
              <span className="block text-xs text-muted-foreground">5-Model Ensemble</span>
            </div>
          </div>
        </div>
        <div className="border-t border-border pt-4 flex flex-wrap justify-between items-center gap-2">
          <p className="text-[11px] text-muted-foreground">© {new Date().getFullYear()} VERIFAI — AI-Powered Fake News Detection</p>
          <p className="text-[11px] text-muted-foreground">Built by <a href="https://github.com/imkoushal" target="_blank" rel="noreferrer" className="text-primary hover:underline">Koushal</a></p>
        </div>
      </div>
    </footer>
  )
}
