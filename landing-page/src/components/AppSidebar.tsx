import { Link, useLocation } from "react-router-dom"
import { ShieldCheck, BarChart3, Search, Layers, ArrowLeftRight, History, Bookmark, Settings, MessageSquarePlus, Info } from "lucide-react"
import { useAuth } from "../context/AuthContext"

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

export function AppSidebar() {
  const { user } = useAuth()
  const location = useLocation()

  return (
    <aside className="hidden md:flex flex-col w-64 h-screen fixed left-0 top-0 bg-sidebar-bg border-r border-border z-40 transition-colors">
      <div className="h-16 flex items-center px-6 border-b border-border/50 shrink-0">
        <Link to="/dashboard" className="flex items-center gap-2">
          <ShieldCheck className="w-6 h-6 text-primary" />
          <span className="font-heading font-bold text-lg tracking-tight">VERIFAI</span>
        </Link>
      </div>

      <div className="flex-1 overflow-y-auto py-6 px-4 space-y-8">
        {navGroups.map((group, i) => (
          <div key={i}>
            <h4 className="text-[10px] font-mono font-semibold text-muted-foreground uppercase tracking-widest mb-3 px-2">
              {group.title}
            </h4>
            <div className="space-y-1">
              {group.items.map(item => {
                const isActive = location.pathname === item.path;
                return (
                  <Link key={item.label} to={item.path}
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

      {user && (
        <div className="p-4 border-t border-border/50 shrink-0">
          <div className="flex items-center gap-3 px-3 py-2 bg-background rounded-xl border border-border shadow-sm">
            <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center text-primary font-bold text-xs shrink-0">
              {user.name?.charAt(0) || user.email?.charAt(0) || "U"}
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-semibold text-foreground truncate">{user.name || "User"}</p>
              <p className="text-[10px] text-muted-foreground truncate">{user.email}</p>
            </div>
          </div>
        </div>
      )}
    </aside>
  )
}
