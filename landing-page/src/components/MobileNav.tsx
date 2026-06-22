import { Link, useLocation } from "react-router-dom"
import { ShieldCheck, BarChart3, Search, Layers, ArrowLeftRight, History, Bookmark, Settings, MessageSquarePlus, Info, X } from "lucide-react"

const navGroups = [
  {
    title: "OVERVIEW",
    items: [
      { path: "/dashboard", icon: Search, label: "Analyze" }
    ]
  },
  {
    title: "TOOLS",
    items: [
      { path: "/compare", icon: ArrowLeftRight, label: "Compare" },
      { path: "/batch", icon: Layers, label: "Batch Analysis" },
    ]
  },
  {
    title: "DATA",
    items: [
      { path: "/analytics", icon: BarChart3, label: "Analytics" },
      { path: "/history", icon: History, label: "History" },
      { path: "/bookmarks", icon: Bookmark, label: "Bookmarks" },
    ]
  },
  {
    title: "SYSTEM",
    items: [
      { path: "/settings", icon: Settings, label: "Settings" },
      { path: "/feedback", icon: MessageSquarePlus, label: "Feedback" },
      { path: "/about", icon: Info, label: "About" },
    ]
  }
]

export function MobileNav({ open, onClose }: { open: boolean, onClose: () => void }) {
  const location = useLocation()

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 md:hidden">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-background/80 backdrop-blur-sm" onClick={onClose} />
      
      {/* Drawer */}
      <div className="absolute left-0 top-0 bottom-0 w-[280px] bg-sidebar-bg border-r border-border shadow-2xl flex flex-col animate-slide-in-left">
        <div className="h-16 flex items-center justify-between px-6 border-b border-border/50 shrink-0">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-6 h-6 text-primary" />
            <span className="font-heading font-bold text-lg tracking-tight">VERIFAI</span>
          </div>
          <button onClick={onClose} className="p-2 text-muted-foreground hover:text-foreground">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto py-6 px-4 space-y-8 scrollbar-thin">
          {navGroups.map((group, i) => (
            <div key={i}>
              <h4 className="text-[10px] font-mono font-semibold text-muted-foreground uppercase tracking-widest mb-3 px-2">
                {group.title}
              </h4>
              <div className="space-y-1">
                {group.items.map(item => {
                  const isActive = location.pathname === item.path;
                  return (
                    <Link key={item.label} to={item.path} onClick={onClose}
                      className={`flex items-center gap-3 px-3 py-2 sidebar-item text-sm font-medium ${
                        isActive ? "sidebar-item-active" : "text-muted-foreground hover:text-foreground"
                      }`}>
                      <item.icon className="w-4 h-4" />
                      {item.label}
                    </Link>
                  )
                })}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
