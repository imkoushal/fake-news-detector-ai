import { useLocation, useNavigate } from "react-router-dom"
import { useAuth } from "../context/AuthContext"
import { Home, BarChart3, History, Settings, Search } from "lucide-react"

const tabs = [
  { path: "/dashboard", icon: Home, label: "Home" },
  { path: "/analytics", icon: Search, label: "Analyze" },
  { path: "/batch", icon: BarChart3, label: "Batch" },
  { path: "/history", icon: History, label: "History" },
  { path: "/settings", icon: Settings, label: "More" },
]

export function MobileNav() {
  const { user } = useAuth()
  const location = useLocation()
  const navigate = useNavigate()

  if (!user) return null

  return (
    <nav className="md:hidden fixed bottom-0 left-0 right-0 z-50 bg-secondary/95 backdrop-blur-lg border-t border-border"
      style={{ paddingBottom: "env(safe-area-inset-bottom, 0px)" }}>
      <div className="flex justify-around items-center h-14">
        {tabs.map(t => {
          const active = location.pathname === t.path
          return (
            <button key={t.path} onClick={() => navigate(t.path)}
              className={`flex flex-col items-center gap-0.5 px-3 py-1.5 transition-colors ${active ? "text-primary" : "text-muted-foreground"}`}>
              <t.icon className="w-5 h-5" />
              <span className="text-[10px] font-medium">{t.label}</span>
            </button>
          )
        })}
      </div>
    </nav>
  )
}

