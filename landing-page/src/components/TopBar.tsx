import { useLocation } from "react-router-dom"
import { Search, LogOut, Menu } from "lucide-react"
import { useAuth } from "../context/AuthContext"

export function TopBar({ onMobileMenuClick }: { onMobileMenuClick: () => void }) {
  const { logout } = useAuth()
  const location = useLocation()
  
  const getPageTitle = () => {
    const path = location.pathname.substring(1)
    if (!path) return "Dashboard"
    return path.charAt(0).toUpperCase() + path.slice(1)
  }

  return (
    <header className="h-16 bg-background/80 backdrop-blur-md border-b border-border flex items-center justify-between px-4 md:px-8 sticky top-0 z-30">
      <div className="flex items-center gap-4">
        <button onClick={onMobileMenuClick} className="md:hidden p-2 text-muted-foreground hover:text-foreground">
          <Menu className="w-5 h-5" />
        </button>
        <div className="hidden md:flex items-center gap-2 text-sm">
          <span className="text-muted-foreground font-medium">VERIFAI</span>
          <span className="text-muted-foreground">/</span>
          <span className="font-semibold text-foreground">{getPageTitle()}</span>
        </div>
      </div>

      <div className="flex items-center gap-4 flex-1 max-w-md justify-end md:justify-center px-4">
        <div className="relative w-full max-w-xs hidden sm:block">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
          <input type="text" placeholder="Search everywhere... (Ctrl+K)" 
            className="w-full bg-secondary border border-border rounded-full pl-9 pr-4 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 transition-all" />
        </div>
      </div>

      <div className="flex items-center gap-3">
        <button onClick={logout} className="p-2 text-muted-foreground hover:text-destructive transition-colors rounded-full hover:bg-destructive/10" title="Sign Out">
          <LogOut className="w-4 h-4" />
        </button>
      </div>
    </header>
  )
}
