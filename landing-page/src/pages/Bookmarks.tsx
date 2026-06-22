import { useState, useEffect } from "react"
import { useAuth } from "../context/AuthContext"
import { Bookmark, Trash2 } from "lucide-react"
import { Button } from "../components/ui/button"

export interface BookmarkItem {
  id: string
  prediction: string
  confidence: number
  confidence_tier: string
  red_flag_score: number
  preview: string
  savedAt: string
}

const STORAGE_KEY = "verifai_bookmarks"

export function getBookmarks(): BookmarkItem[] {
  try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]") } catch { return [] }
}

export function addBookmark(result: any, text: string) {
  const bookmarks = getBookmarks()
  const item: BookmarkItem = {
    id: Date.now().toString(),
    prediction: result.prediction,
    confidence: result.confidence,
    confidence_tier: result.confidence_tier,
    red_flag_score: result.red_flag_score ?? 0,
    preview: text.slice(0, 120),
    savedAt: new Date().toISOString(),
  }
  bookmarks.unshift(item)
  localStorage.setItem(STORAGE_KEY, JSON.stringify(bookmarks.slice(0, 200)))
  return item
}

export function removeBookmark(id: string) {
  const bookmarks = getBookmarks().filter(b => b.id !== id)
  localStorage.setItem(STORAGE_KEY, JSON.stringify(bookmarks))
}

export function BookmarksPage() {
  const { user } = useAuth()
  const [bookmarks, setBookmarks] = useState<BookmarkItem[]>([])

  useEffect(() => { setBookmarks(getBookmarks()) }, [])

  if (!user) return <div className="min-h-screen bg-background flex items-center justify-center text-foreground"><p>Please sign in.</p></div>

  const handleRemove = (id: string) => {
    removeBookmark(id)
    setBookmarks(getBookmarks())
  }

  return (
    <div className="min-h-screen bg-background pt-24 px-4 md:px-12 lg:px-20 text-foreground pb-20">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold tracking-tight mb-2">Bookmarks</h1>
        <p className="text-muted-foreground text-sm mb-8">{bookmarks.length} saved analyses</p>

        {bookmarks.length === 0 ? (
          <div className="bg-secondary border border-border border-dashed rounded-xl p-10 text-center">
            <Bookmark className="w-10 h-10 text-muted mx-auto mb-3" />
            <h3 className="text-foreground font-medium mb-1">No bookmarks yet</h3>
            <p className="text-muted-foreground text-sm">Bookmark analysis results from the Dashboard to save them here.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {bookmarks.map(b => (
              <div key={b.id} className="bg-secondary border border-border rounded-xl p-4 flex items-start gap-4 hover:bg-secondary/80 transition-colors">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${b.prediction === "FAKE" ? "bg-destructive/15 text-destructive" : "bg-[#4ADE80]/15 text-[#4ADE80]"}`}>{b.prediction}</span>
                    <span className="text-xs text-muted-foreground">{b.confidence.toFixed(1)}%</span>
                    <span className="text-xs text-muted-foreground">· {b.red_flag_score}/10 flags</span>
                    <span className="text-xs text-muted-foreground ml-auto">{b.savedAt.split("T")[0]}</span>
                  </div>
                  <p className="text-sm text-foreground truncate">{b.preview}</p>
                </div>
                <Button variant="outline" size="sm" onClick={() => handleRemove(b.id)} className="shrink-0 text-destructive border-destructive/30 hover:bg-destructive/10">
                  <Trash2 className="w-3.5 h-3.5" />
                </Button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
