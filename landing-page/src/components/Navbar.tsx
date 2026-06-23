import { useState } from "react"
import { Link } from "react-router-dom"
import { Button } from "./ui/button"
import { useAuth } from "../context/AuthContext"
import { Menu, X } from "lucide-react"

export function Navbar() {
  const { user, setShowAuthModal } = useAuth()
  const [mobileOpen, setMobileOpen] = useState(false)

  return (
    <nav className="fixed top-4 left-1/2 -translate-x-1/2 z-50 w-[calc(100%-2rem)] max-w-5xl">
      <div className="glass-nav rounded-2xl px-6 py-3 flex items-center justify-between shadow-card">
        {/* Logo */}
        <Link to="/" className="text-foreground text-xl font-bold font-heading tracking-tight">
          VERIF<span className="text-primary">AI</span>
        </Link>

        {/* Desktop links */}
        <div className="hidden md:flex items-center gap-8 text-sm font-medium text-muted-foreground">
          <a href="/#how-it-works" className="hover:text-foreground transition-colors">How It Works</a>
          <a href="/#accuracy" className="hover:text-foreground transition-colors">Accuracy</a>
          <Link to="/about" className="hover:text-foreground transition-colors">About</Link>
        </div>

        {/* CTA */}
        <div className="hidden md:flex items-center gap-3">
          {user ? (
            <Link to="/dashboard">
              <Button className="btn-gradient rounded-full px-6 h-10 text-sm font-semibold">
                Open Dashboard
              </Button>
            </Link>
          ) : (
            <Button onClick={() => setShowAuthModal(true)}
              className="btn-gradient rounded-full px-6 h-10 text-sm font-semibold">
              Get Started Free
            </Button>
          )}
        </div>

        {/* Mobile hamburger */}
        <button onClick={() => setMobileOpen(!mobileOpen)} className="md:hidden w-9 h-9 rounded-lg flex items-center justify-center hover:bg-secondary/50 transition-colors">
          {mobileOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>
      </div>

      {/* Mobile dropdown */}
      {mobileOpen && (
        <div className="md:hidden mt-2 glass-nav rounded-2xl p-5 flex flex-col gap-3 animate-fade-up shadow-card-lg">
          <a href="/#how-it-works" onClick={() => setMobileOpen(false)} className="text-sm text-muted-foreground hover:text-foreground py-1.5">How It Works</a>
          <a href="/#accuracy" onClick={() => setMobileOpen(false)} className="text-sm text-muted-foreground hover:text-foreground py-1.5">Accuracy</a>
          <Link to="/about" onClick={() => setMobileOpen(false)} className="text-sm text-muted-foreground hover:text-foreground py-1.5">About</Link>
          <div className="border-t border-border/50 pt-3 mt-1">
            {user ? (
              <Link to="/dashboard" onClick={() => setMobileOpen(false)}>
                <Button className="btn-gradient rounded-full w-full h-10 text-sm font-semibold">Open Dashboard</Button>
              </Link>
            ) : (
              <Button onClick={() => { setShowAuthModal(true); setMobileOpen(false) }}
                className="btn-gradient rounded-full w-full h-10 text-sm font-semibold">
                Get Started Free
              </Button>
            )}
          </div>
        </div>
      )}
    </nav>
  )
}
