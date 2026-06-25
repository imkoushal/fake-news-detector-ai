import { useState, useEffect } from "react"
import { useAuth } from "../context/AuthContext"
import { useToast } from "../context/ToastContext"
import { Sun, Moon, Type, Trash2, Download } from "lucide-react"
import { Button } from "../components/ui/button"
import { API_BASE, getAuthHeaders } from "../lib/api"

export function SettingsPage() {
  const { user } = useAuth()
  const { toast } = useToast()

  const [theme, setTheme] = useState(() => localStorage.getItem("verifai_theme") || "dark")
  const [typo, setTypo] = useState(() => localStorage.getItem("verifai_typo") || "standard")
  const [sensitivity, setSensitivity] = useState(() => parseInt(localStorage.getItem("verifai_sensitivity") || "50"))
  const [translate, setTranslate] = useState(() => localStorage.getItem("verifai_translate") === "true")

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme)
    localStorage.setItem("verifai_theme", theme)
  }, [theme])

  useEffect(() => { localStorage.setItem("verifai_sensitivity", String(sensitivity)) }, [sensitivity])
  useEffect(() => { localStorage.setItem("verifai_translate", String(translate)) }, [translate])
  useEffect(() => {
    localStorage.setItem("verifai_typo", typo)
    document.documentElement.style.fontSize = typo === "compact" ? "14px" : typo === "legibility" ? "18px" : "16px"
  }, [typo])

  if (!user) return <div className="min-h-screen bg-background flex items-center justify-center text-foreground"><p>Please sign in.</p></div>

  const exportTelemetry = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/history`, { headers: getAuthHeaders() })
      const data = await res.json()
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" })
      const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = "verifai-telemetry.json"; a.click()
      toast("Telemetry exported!", "success")
    } catch { toast("Export failed.", "error") }
  }

  const purgeArchives = async () => {
    if (!confirm("This will delete all your analysis history. Continue?")) return
    try {
      await fetch(`${API_BASE}/api/v1/history`, { method: "DELETE", headers: getAuthHeaders() })
      toast("History cleared.", "success")
    } catch { toast("Purge failed.", "error") }
  }

  return (
    <div className="bg-background p-6 md:p-8 text-foreground">
      <div className="max-w-2xl mx-auto">
        <h1 className="text-2xl font-heading font-extrabold tracking-tight mb-2">Settings</h1>
        <p className="text-muted-foreground text-sm mb-10">Customize your VERIFAI experience.</p>

        <div className="space-y-6">
          {/* Theme */}
          <div className="card-enterprise p-5">
            <h3 className="text-sm font-semibold mb-4">Appearance</h3>
            <div className="flex gap-3">
              {[
                { val: "dark", icon: Moon, label: "Dark" },
                { val: "light", icon: Sun, label: "Light" },
              ].map(t => (
                <button key={t.val} onClick={() => setTheme(t.val)}
                  className={`flex-1 flex items-center justify-center gap-2 p-3 rounded-lg border transition-colors ${theme === t.val ? "bg-primary/10 border-primary/40 text-primary" : "border-border text-muted-foreground hover:text-foreground"}`}>
                  <t.icon className="w-4 h-4" /> <span className="text-sm">{t.label}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Typography */}
          <div className="card-enterprise p-5">
            <h3 className="text-sm font-semibold mb-4 flex items-center gap-2"><Type className="w-4 h-4" /> Typography Scale</h3>
            <div className="flex gap-3">
              {["compact", "standard", "legibility"].map(t => (
                <button key={t} onClick={() => setTypo(t)}
                  className={`flex-1 p-3 rounded-lg border text-sm capitalize transition-colors ${typo === t ? "bg-primary/10 border-primary/40 text-primary" : "border-border text-muted-foreground hover:text-foreground"}`}>
                  {t}
                </button>
              ))}
            </div>
          </div>

          {/* Sensitivity */}
          <div className="card-enterprise p-5">
            <h3 className="text-sm font-semibold mb-4">Default Sensitivity</h3>
            <div className="flex items-center gap-4">
              <span className="text-xs text-muted-foreground">Lenient</span>
              <input type="range" min={0} max={100} value={sensitivity} onChange={e => setSensitivity(+e.target.value)}
                className="flex-1 h-1 accent-primary cursor-pointer" />
              <span className="text-xs text-muted-foreground">Strict</span>
              <span className="text-sm font-medium text-primary w-12 text-right">{(sensitivity / 100).toFixed(2)}</span>
            </div>
          </div>

          {/* Translate */}
          <div className="card-enterprise p-5 flex items-center justify-between">
            <div>
              <h3 className="text-sm font-semibold">Auto-Translate</h3>
              <p className="text-xs text-muted-foreground mt-1">Translate non-English input before analysis</p>
            </div>
            <button onClick={() => setTranslate(!translate)}
              className={`w-11 h-6 rounded-full transition-colors relative ${translate ? "bg-primary" : "bg-muted"}`}>
              <span className={`absolute top-1 w-4 h-4 rounded-full bg-white transition-all ${translate ? "left-6" : "left-1"}`} />
            </button>
          </div>

          {/* Data */}
          <div className="card-enterprise p-5">
            <h3 className="text-sm font-semibold mb-4">Data Management</h3>
            <div className="flex gap-3">
              <Button variant="outline" size="sm" className="flex-1" onClick={exportTelemetry}>
                <Download className="w-4 h-4 mr-2" /> Export Telemetry
              </Button>
              <Button variant="outline" size="sm" className="flex-1 text-destructive border-destructive/30 hover:bg-destructive/10" onClick={purgeArchives}>
                <Trash2 className="w-4 h-4 mr-2" /> Purge Archives
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
