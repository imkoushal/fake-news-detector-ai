import { useLocation, useNavigate } from "react-router-dom"
import { useAuth } from "../context/AuthContext"
import { Home, BarChart3, History, Settings, Layers } from "lucide-react"

const tabs = [
  { path: "/dashboard", icon: Home, label: "Home" },
  { path: "/batch", icon: Layers, label: "Batch" },
  { path: "/analytics", icon: BarChart3, label: "Stats" },
  { path: "/history", icon: History, label: "History" },
  { path: "/settings", icon: Settings, label: "Settings" },
]

export function MobileNav() {
  const { user } = useAuth()
  const location = useLocation()
  const navigate = useNavigate()

  if (!user) return null

  return (
    <nav className="md:hidden fixed bottom-0 left-0 right-0 z-50 bg-secondary/95 backdrop-blur-lg border-t border-border safe-area-bottom">
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
