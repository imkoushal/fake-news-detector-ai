import { Link, useLocation } from "react-router-dom"
import { useAuth } from "../context/AuthContext"
import {
  LayoutDashboard, Search, ArrowLeftRight, Layers,
  History, Bookmark, Settings, MessageSquare,
  Info, LogOut, Sun, Moon, ChevronLeft, ChevronRight
} from "lucide-react"
import { useState, useEffect } from "react"

const navGroups = [
  {
    label: "Overview",
    items: [
      { path: "/dashboard", icon: LayoutDashboard, label: "Dashboard" },
    ],
  },
  {
    label: "Analysis",
    items: [
      { path: "/analytics", icon: Search, label: "Analyze" },
      { path: "/compare", icon: ArrowLeftRight, label: "Compare" },
      { path: "/batch", icon: Layers, label: "Batch Analysis" },
    ],
  },
  {
    label: "Data",
    items: [
      { path: "/history", icon: History, label: "History" },
      { path: "/bookmarks", icon: Bookmark, label: "Bookmarks" },
    ],
  },
  {
    label: "System",
    items: [
      { path: "/settings", icon: Settings, label: "Settings" },
      { path: "/feedback", icon: MessageSquare, label: "Feedback" },
      { path: "/about", icon: Info, label: "About" },
    ],
  },
]

export function AppSidebar({ collapsed, onToggle }: { collapsed: boolean; onToggle: () => void }) {
  const { user, logout } = useAuth()
  const location = useLocation()
  const [theme, setTheme] = useState<"dark" | "light">(
    () => (localStorage.getItem("verifai_theme") as "dark" | "light") || "dark"
  )

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme)
    localStorage.setItem("verifai_theme", theme)
  }, [theme])

  const initials = user?.name?.split(" ").map(n => n[0]).join("").slice(0, 2).toUpperCase() || "U"

  const isActive = (path: string) => {
    if (path === "/dashboard") return location.pathname === "/dashboard"
    return location.pathname === path
  }

  return (
    <aside className={`fixed top-0 left-0 h-screen bg-sidebar-bg border-r border-border z-40 flex flex-col transition-all duration-300 ${collapsed ? "w-[68px]" : "w-[240px]"}`}>
      {/* Logo */}
      <div className="h-16 flex items-center px-5 border-b border-border shrink-0">
        <Link to="/dashboard" className="flex items-center gap-2.5 overflow-hidden">
          <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center shrink-0">
            <span className="text-white text-sm font-bold font-heading">V</span>
          </div>
          {!collapsed && <span className="text-foreground text-lg font-bold font-heading tracking-tight whitespace-nowrap">VERIF<span className="text-primary">AI</span></span>}
        </Link>
      </div>

      {/* Nav groups */}
      <nav className="flex-1 overflow-y-auto py-4 px-3 space-y-6">
        {navGroups.map(group => (
          <div key={group.label}>
            {!collapsed && (
              <p className="text-[10px] uppercase tracking-widest text-muted-foreground/60 font-mono font-semibold px-3 mb-2">{group.label}</p>
            )}
            <div className="space-y-0.5">
              {group.items.map(item => {
                const active = isActive(item.path)
                return (
                  <Link key={item.label} to={item.path}
                    className={`flex items-center gap-3 px-3 py-2 rounded-[10px] transition-all duration-150 group relative
                      ${active
                        ? "bg-primary text-white shadow-sm"
                        : "text-muted-foreground hover:bg-sidebar-hover hover:text-foreground"
                      }`}
                    title={collapsed ? item.label : undefined}>
                    <item.icon className={`w-[18px] h-[18px] shrink-0 ${active ? "text-white" : "text-muted-foreground group-hover:text-foreground"}`} />
                    {!collapsed && <span className="text-[13px] font-medium whitespace-nowrap">{item.label}</span>}
                    {collapsed && (
                      <div className="absolute left-full ml-2 px-2.5 py-1 bg-foreground text-background text-xs font-medium rounded-md opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity whitespace-nowrap z-50">
                        {item.label}
                      </div>
                    )}
                  </Link>
                )
              })}
            </div>
          </div>
        ))}
      </nav>

      {/* Bottom section */}
      <div className="border-t border-border p-3 space-y-2 shrink-0">
        {/* Theme toggle */}
        <button onClick={() => setTheme(t => t === "dark" ? "light" : "dark")}
          className="w-full flex items-center gap-3 px-3 py-2 rounded-[10px] text-muted-foreground hover:bg-sidebar-hover hover:text-foreground transition-all">
          {theme === "dark" ? <Sun className="w-[18px] h-[18px] shrink-0" /> : <Moon className="w-[18px] h-[18px] shrink-0" />}
          {!collapsed && <span className="text-[13px] font-medium">{theme === "dark" ? "Light Mode" : "Dark Mode"}</span>}
        </button>

        {/* Collapse toggle */}
        <button onClick={onToggle}
          className="w-full flex items-center gap-3 px-3 py-2 rounded-[10px] text-muted-foreground hover:bg-sidebar-hover hover:text-foreground transition-all">
          {collapsed ? <ChevronRight className="w-[18px] h-[18px] shrink-0" /> : <ChevronLeft className="w-[18px] h-[18px] shrink-0" />}
          {!collapsed && <span className="text-[13px] font-medium">Collapse</span>}
        </button>

        {/* User card */}
        <div className={`flex items-center gap-3 px-3 py-2.5 rounded-xl bg-secondary/50 border border-border/50 ${collapsed ? "justify-center" : ""}`}>
          {user?.avatar_url ? (
            <img src={user.avatar_url} className="w-8 h-8 rounded-full object-cover shrink-0" alt="" />
          ) : (
            <div className="w-8 h-8 rounded-full bg-primary/15 text-primary text-xs font-bold flex items-center justify-center shrink-0">{initials}</div>
          )}
          {!collapsed && (
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-foreground truncate">{user?.name}</p>
              <p className="text-[10px] text-muted-foreground truncate">{user?.email}</p>
            </div>
          )}
        </div>

        {/* Sign out */}
        <button onClick={logout}
          className="w-full flex items-center gap-3 px-3 py-2 rounded-[10px] text-destructive/70 hover:bg-destructive/10 hover:text-destructive transition-all">
          <LogOut className="w-[18px] h-[18px] shrink-0" />
          {!collapsed && <span className="text-[13px] font-medium">Sign Out</span>}
        </button>
      </div>
    </aside>
  )
}
