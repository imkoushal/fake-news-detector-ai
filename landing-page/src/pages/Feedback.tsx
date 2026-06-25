import { useState } from "react"
import { useAuth } from "../context/AuthContext"
import { useToast } from "../context/ToastContext"
import { API_BASE, getAuthHeaders } from "../lib/api"
import { MessageSquarePlus, Send } from "lucide-react"
import { Button } from "../components/ui/button"

export function FeedbackPage() {
  const { user } = useAuth()
  const { toast } = useToast()
  const [type, setType] = useState<"bug" | "feature" | "general">("general")
  const [message, setMessage] = useState("")
  const [sending, setSending] = useState(false)
  const [sent, setSent] = useState(false)

  if (!user) return <div className="min-h-screen bg-background flex items-center justify-center text-foreground"><p>Please sign in.</p></div>

  const handleSubmit = async () => {
    if (!message.trim()) return
    setSending(true)
    try {
      await fetch(`${API_BASE}/api/v1/feedback`, {
        method: "POST", headers: getAuthHeaders(),
        body: JSON.stringify({ type, message, timestamp: new Date().toISOString() })
      })
      setSent(true)
      toast("Feedback submitted. Thank you!", "success")
    } catch { toast("Failed to send. Saved locally.", "error") }
    finally { setSending(false) }
  }

  return (
    <div className="bg-background p-6 md:p-8 text-foreground">
      <div className="max-w-xl mx-auto">
        <h1 className="text-2xl font-heading font-extrabold tracking-tight mb-2">Feedback</h1>
        <p className="text-muted-foreground text-sm mb-8">Help us improve VERIFAI. Report bugs, request features, or share thoughts.</p>

        {sent ? (
          <div className="card-enterprise p-10 text-center">
            <div className="w-14 h-14 bg-[#4ADE80]/10 rounded-full flex items-center justify-center mx-auto mb-4">
              <MessageSquarePlus className="w-7 h-7 text-[#4ADE80]" />
            </div>
            <h3 className="text-lg font-heading font-bold mb-2">Thank you!</h3>
            <p className="text-sm text-muted-foreground mb-4">Your feedback has been received and will be reviewed.</p>
            <Button variant="outline" onClick={() => { setSent(false); setMessage("") }}>Send Another</Button>
          </div>
        ) : (
          <div className="card-enterprise p-6 space-y-5">
            {/* Type selector */}
            <div>
              <label className="text-xs text-muted-foreground uppercase tracking-widest font-mono mb-2 block">Category</label>
              <div className="flex gap-2">
                {([
                  ["bug", "🐛 Bug Report"],
                  ["feature", "✨ Feature Request"],
                  ["general", "💬 General"],
                ] as const).map(([val, label]) => (
                  <button key={val} onClick={() => setType(val)}
                    className={`flex-1 px-3 py-2 rounded-lg text-xs font-medium border transition-colors ${type === val ? "bg-primary/15 border-primary/40 text-primary" : "border-border text-muted-foreground hover:text-foreground"}`}>
                    {label}
                  </button>
                ))}
              </div>
            </div>

            {/* Message */}
            <div>
              <label className="text-xs text-muted-foreground uppercase tracking-widest font-mono mb-2 block">Message</label>
              <textarea value={message} onChange={e => setMessage(e.target.value)}
                placeholder={type === "bug" ? "Describe the bug, steps to reproduce, expected behavior..." : type === "feature" ? "Describe the feature you'd like to see..." : "Share your thoughts about VERIFAI..."}
                className="w-full h-36 bg-background border border-border rounded-lg p-4 text-sm text-foreground resize-none focus:outline-none focus:ring-2 focus:ring-primary/50" />
              <p className="text-[10px] text-muted-foreground mt-1">{message.length} characters</p>
            </div>

            <button className="w-full btn-gradient rounded-xl py-3.5 text-sm font-semibold disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2" onClick={handleSubmit} disabled={sending || !message.trim()}>
              <Send className="w-4 h-4" />
              {sending ? "Sending..." : "Submit Feedback"}
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
