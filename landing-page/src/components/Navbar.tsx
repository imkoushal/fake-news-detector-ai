import { Link, useNavigate } from "react-router-dom"
import { Button } from "./ui/button"
import { useAuth } from "../context/AuthContext"

export function Navbar() {
  const { user, setShowAuthModal } = useAuth();
  const navigate = useNavigate();

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 flex justify-between px-8 lg:px-16 py-5 bg-background/80 backdrop-blur-md border-b border-border/50">
      <div className="flex items-center">
        <Link to="/" className="text-foreground text-xl font-semibold tracking-tight">
          VERIF<span className="text-primary">AI</span>
        </Link>
      </div>
      
      <div className="hidden md:flex items-center gap-8 text-sm text-muted-foreground uppercase tracking-widest">
        <a href="/#how-it-works" className="hover:text-foreground transition-colors">How It Works</a>
        <a href="/#accuracy" className="hover:text-foreground transition-colors">Accuracy</a>
        <a href="/#api" className="hover:text-foreground transition-colors">API</a>
        <a href="/#github" className="hover:text-foreground transition-colors">GitHub</a>
      </div>

      <div className="hidden md:inline-flex items-center">
        {user ? (
          <Button 
            variant="navCta" 
            size="lg" 
            className="rounded-lg uppercase text-xs tracking-widest px-6"
            onClick={() => navigate('/dashboard')}
          >
            Dashboard
          </Button>
        ) : (
          <Button 
            variant="navCta" 
            size="lg" 
            className="rounded-lg uppercase text-xs tracking-widest px-6"
            onClick={() => setShowAuthModal(true)}
          >
            Try It Free
          </Button>
        )}
      </div>
    </nav>
  )
}
