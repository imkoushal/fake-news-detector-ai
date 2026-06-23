import { useLocation } from "react-router-dom"
import { Search, Menu } from "lucide-react"
import { useState } from "react"

const pageNames: Record<string, string> = {
  "/dashboard": "Dashboard",
  "/compare": "Compare",
  "/batch": "Batch Analysis",
  "/analytics": "Analytics",
  "/history": "History",
  "/bookmarks": "Bookmarks",
  "/settings": "Settings",
  "/feedback": "Feedback",
  "/about": "About",
}

export function TopBar({ onMobileMenuToggle }: { onMobileMenuToggle: () => void }) {
  const location = useLocation()
  const [searchQuery, setSearchQuery] = useState("")
  const pageName = pageNames[location.pathname] || "Dashboard"

  return (
    <header className="h-16 border-b border-border bg-background/80 backdrop-blur-sm flex items-center justify-between px-6 gap-4 shrink-0 sticky top-0 z-30">
      {/* Left: Mobile menu + breadcrumb */}
      <div className="flex items-center gap-3">
        <button onClick={onMobileMenuToggle} className="md:hidden w-9 h-9 rounded-lg border border-border flex items-center justify-center hover:bg-secondary transition-colors">
          <Menu className="w-4 h-4 text-muted-foreground" />
        </button>
        <div className="flex items-center gap-2 text-sm">
          <span className="text-muted-foreground hidden sm:inline">VERIFAI</span>
          <span className="text-muted-foreground/40 hidden sm:inline">/</span>
          <span className="font-semibold text-foreground">{pageName}</span>
        </div>
      </div>

      {/* Center: Search */}
      <div className="flex-1 max-w-md hidden sm:block">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search views or features..."
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            className="w-full h-9 pl-9 pr-4 bg-secondary border border-border rounded-lg text-sm text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-2 focus:ring-primary/30 transition-all"
          />
          <kbd className="absolute right-3 top-1/2 -translate-y-1/2 text-[10px] text-muted-foreground/40 font-mono border border-border/50 px-1.5 py-0.5 rounded hidden lg:inline">⌘K</kbd>
        </div>
      </div>

      {/* Right: empty — user card is in sidebar */}
      <div className="w-9" />
    </header>
  )
}
