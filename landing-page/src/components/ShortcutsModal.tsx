import { useState, useEffect } from "react"
import { X } from "lucide-react"

const shortcuts = [
  { keys: ["Ctrl", "Enter"], desc: "Analyze current input" },
  { keys: ["?"], desc: "Show this shortcuts panel" },
  { keys: ["Ctrl", "K"], desc: "Focus search / input" },
  { keys: ["Esc"], desc: "Close modals & panels" },
  { keys: ["Alt", "1"], desc: "Switch to Text tab" },
  { keys: ["Alt", "2"], desc: "Switch to URL tab" },
  { keys: ["Alt", "3"], desc: "Switch to Audio tab" },
]

export function ShortcutsModal() {
  const [open, setOpen] = useState(false)

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "?" && !["INPUT", "TEXTAREA"].includes((e.target as HTMLElement).tagName)) {
        e.preventDefault(); setOpen(o => !o)
      }
      if (e.key === "Escape") setOpen(false)
    }
    document.addEventListener("keydown", handler)
    return () => document.removeEventListener("keydown", handler)
  }, [])

  if (!open) return null

  return (
    <div className="fixed inset-0 z-[200] flex items-center justify-center bg-black/50 backdrop-blur-sm" onClick={() => setOpen(false)}>
      <div className="bg-secondary border border-border rounded-2xl p-6 w-full max-w-md shadow-2xl animate-fade-up" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-lg font-bold text-foreground">Keyboard Shortcuts</h2>
          <button onClick={() => setOpen(false)} className="text-muted-foreground hover:text-foreground transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>
        <div className="space-y-2">
          {shortcuts.map((s, i) => (
            <div key={i} className="flex items-center justify-between py-2 border-b border-border/50 last:border-0">
              <span className="text-sm text-foreground">{s.desc}</span>
              <div className="flex gap-1">
                {s.keys.map((k, j) => (
                  <kbd key={j} className="px-2 py-0.5 bg-background border border-border rounded text-[11px] font-mono text-muted-foreground">{k}</kbd>
                ))}
              </div>
            </div>
          ))}
        </div>
        <p className="text-[10px] text-muted-foreground mt-4 text-center">Press <kbd className="px-1.5 py-0.5 bg-background border border-border rounded text-[10px] font-mono">?</kbd> to toggle</p>
      </div>
    </div>
  )
}
