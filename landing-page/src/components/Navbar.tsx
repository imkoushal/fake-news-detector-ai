import { useState, useEffect, useRef } from "react"
import { Link, useNavigate } from "react-router-dom"
import { Button } from "./ui/button"
import { useAuth } from "../context/AuthContext"
import { Sun, Moon, Menu, X, LogOut, User, ChevronDown } from "lucide-react"

export function Navbar() {
  const { user, logout, setShowAuthModal } = useAuth()
  const navigate = useNavigate()
  const [theme, setTheme] = useState<"dark" | "light">(
    () => (localStorage.getItem("verifai_theme") as "dark" | "light") || "dark"
  )
  const [mobileOpen, setMobileOpen] = useState(false)
  const [dropdownOpen, setDropdownOpen] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)

  // Apply theme
  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme)
    localStorage.setItem("verifai_theme", theme)
  }, [theme])

  // Close dropdown on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) setDropdownOpen(false)
    }
    document.addEventListener("mousedown", handler)
    return () => document.removeEventListener("mousedown", handler)
  }, [])

  const toggleTheme = () => setTheme(t => t === "dark" ? "light" : "dark")
  const initials = user?.name?.split(" ").map(n => n[0]).join("").slice(0, 2).toUpperCase() || "U"

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 flex justify-between items-center px-6 lg:px-16 py-4 bg-background/80 backdrop-blur-md border-b border-border/50">
      <Link to="/" className="text-foreground text-xl font-semibold tracking-tight">
        VERIF<span className="text-primary">AI</span>
      </Link>

      {/* Desktop nav links */}
      <div className="hidden md:flex items-center gap-6 text-sm text-muted-foreground">
        <Link to="/about" className="hover:text-foreground transition-colors">About</Link>
        <a href="/#how-it-works" className="hover:text-foreground transition-colors">How It Works</a>
        <a href="/#accuracy" className="hover:text-foreground transition-colors">Accuracy</a>
      </div>

      {/* Right section */}
      <div className="flex items-center gap-3">
        {/* Theme toggle */}
        <button onClick={toggleTheme} className="w-9 h-9 rounded-lg bg-secondary border border-border flex items-center justify-center hover:bg-muted transition-colors" title="Toggle theme">
          {theme === "dark" ? <Sun className="w-4 h-4 text-muted-foreground" /> : <Moon className="w-4 h-4 text-muted-foreground" />}
        </button>

        {/* User section */}
        {user ? (
          <div className="relative hidden md:block" ref={dropdownRef}>
            <button onClick={() => setDropdownOpen(!dropdownOpen)}
              className="flex items-center gap-2 pl-1 pr-3 py-1 rounded-lg bg-secondary border border-border hover:bg-muted transition-colors">
              {user.avatar_url ? (
                <img src={user.avatar_url} className="w-7 h-7 rounded-full object-cover" alt="" />
              ) : (
                <div className="w-7 h-7 rounded-full bg-primary/20 text-primary text-xs font-bold flex items-center justify-center">{initials}</div>
              )}
              <span className="text-xs font-medium text-foreground max-w-[80px] truncate">{user.name}</span>
              <ChevronDown className={`w-3.5 h-3.5 text-muted-foreground transition-transform ${dropdownOpen ? "rotate-180" : ""}`} />
            </button>

            {dropdownOpen && (
              <div className="absolute right-0 mt-2 w-56 bg-secondary border border-border rounded-xl shadow-xl overflow-hidden animate-fade-in">
                <div className="px-4 py-3 border-b border-border">
                  <p className="text-sm font-medium text-foreground truncate">{user.name}</p>
                  <p className="text-xs text-muted-foreground truncate">{user.email}</p>
                </div>
                <button onClick={() => { navigate("/dashboard"); setDropdownOpen(false) }}
                  className="w-full flex items-center gap-2 px-4 py-2.5 text-sm text-foreground hover:bg-background/50 transition-colors">
                  <User className="w-4 h-4" /> Dashboard
                </button>
                <button onClick={() => { navigate("/batch"); setDropdownOpen(false) }}
                  className="w-full flex items-center gap-2 px-4 py-2.5 text-sm text-foreground hover:bg-background/50 transition-colors">
                  📊 Batch Analysis
                </button>
                <button onClick={() => { navigate("/analytics"); setDropdownOpen(false) }}
                  className="w-full flex items-center gap-2 px-4 py-2.5 text-sm text-foreground hover:bg-background/50 transition-colors">
                  📈 Analytics
                </button>
                <button onClick={() => { navigate("/history"); setDropdownOpen(false) }}
                  className="w-full flex items-center gap-2 px-4 py-2.5 text-sm text-foreground hover:bg-background/50 transition-colors">
                  📜 History
                </button>
                <button onClick={() => { navigate("/settings"); setDropdownOpen(false) }}
                  className="w-full flex items-center gap-2 px-4 py-2.5 text-sm text-foreground hover:bg-background/50 transition-colors">
                  ⚙️ Settings
                </button>
                <div className="border-t border-border">
                  <button onClick={() => { logout(); setDropdownOpen(false) }}
                    className="w-full flex items-center gap-2 px-4 py-2.5 text-sm text-destructive hover:bg-destructive/10 transition-colors">
                    <LogOut className="w-4 h-4" /> Sign Out
                  </button>
                </div>
              </div>
            )}
          </div>
        ) : (
          <Button variant="navCta" size="lg" className="hidden md:inline-flex rounded-lg uppercase text-xs tracking-widest px-6"
            onClick={() => setShowAuthModal(true)}>
            Try It Free
          </Button>
        )}

        {/* Mobile hamburger */}
        <button onClick={() => setMobileOpen(!mobileOpen)} className="md:hidden w-9 h-9 rounded-lg bg-secondary border border-border flex items-center justify-center">
          {mobileOpen ? <X className="w-4 h-4" /> : <Menu className="w-4 h-4" />}
        </button>
      </div>

      {/* Mobile menu */}
      {mobileOpen && (
        <div className="absolute top-full left-0 right-0 bg-background border-b border-border p-6 flex flex-col gap-4 md:hidden animate-fade-in">
          <Link to="/about" onClick={() => setMobileOpen(false)} className="text-sm text-muted-foreground hover:text-foreground">About</Link>
          <a href="/#how-it-works" onClick={() => setMobileOpen(false)} className="text-sm text-muted-foreground hover:text-foreground">How It Works</a>
          {user ? (
            <>
              <Link to="/dashboard" onClick={() => setMobileOpen(false)} className="text-sm text-foreground font-medium">Dashboard</Link>
              <button onClick={() => { logout(); setMobileOpen(false) }} className="text-sm text-destructive text-left">Sign Out</button>
            </>
          ) : (
            <Button onClick={() => { setShowAuthModal(true); setMobileOpen(false) }} className="w-full">Try It Free</Button>
          )}
        </div>
      )}
    </nav>
  )
}
