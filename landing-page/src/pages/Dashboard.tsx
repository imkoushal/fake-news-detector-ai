import { useState, useEffect, useMemo } from "react"
import { useAuth } from "../context/AuthContext"
import { API_BASE, getAuthHeaders } from "../lib/api"
import { Loader2 } from "lucide-react"
import { useIsMobile } from "../hooks/useIsMobile"
import { DashboardDesktop } from "./desktop/DashboardDesktop"
import { DashboardMobile } from "./mobile/DashboardMobile"

/** Shared prop interface for desktop/mobile dashboard views */
export interface DashboardViewProps {
  user: any
  greeting: string
  totalAnalyzed: number
  fakeCount: number
  realCount: number
  avgConf: number
  fakePercent: string
  realPercent: string
  total: number
  confBuckets: { label: string; min: number; max: number; count: number }[]
  topicMap: [string, { real: number; fake: number }][]
  allHistory: any[]
  filtered: any[]
  range: 7 | 30 | 90 | 0
  setRange: (v: 7 | 30 | 90 | 0) => void
  community: any
}

export function Dashboard() {
  const { user } = useAuth()
  const isMobile = useIsMobile()
  const [stats, setStats] = useState<any>(null)
  const [community, setCommunity] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [range, setRange] = useState<7 | 30 | 90 | 0>(0)

  useEffect(() => {
    if (!user) return
    Promise.all([
      fetch(`${API_BASE}/api/v1/community-stats`).then(r => r.ok ? r.json() : null),
      fetch(`${API_BASE}/api/v1/user/history?limit=500`, { headers: getAuthHeaders() }).then(r => r.ok ? r.json() : null),
    ]).then(([comm, history]) => {
      const rows = history?.items ?? history?.analyses ?? history ?? []
      const normalized = rows.map((h: any) => ({
        ...h,
        text_preview: h.text_preview ?? h.preview ?? "",
        timestamp: h.timestamp ?? h.date ?? h.created_at ?? "",
        red_flag_score: h.red_flag_score ?? (typeof h.red_flags === 'number' ? h.red_flags / 100 : 0),
      }))
      setCommunity(comm)
      setStats(normalized)
    }).catch(() => {}).finally(() => setLoading(false))
  }, [user])

  const allHistory = stats || []

  const filtered = useMemo(() => {
    if (range === 0) return allHistory
    const cutoff = new Date(); cutoff.setDate(cutoff.getDate() - range)
    return allHistory.filter((h: any) => h.timestamp && new Date(h.timestamp) >= cutoff)
  }, [allHistory, range])

  const totalAnalyzed = filtered.length
  const fakeCount = filtered.filter((h: any) => h.prediction === "FAKE").length
  const realCount = filtered.filter((h: any) => h.prediction === "REAL").length
  const avgConf = filtered.length > 0 ? (filtered.reduce((s: number, h: any) => s + (h.confidence || 0), 0) / filtered.length) : 0
  const total = realCount + fakeCount || 1
  const fakePercent = ((fakeCount / total) * 100).toFixed(1)
  const realPercent = ((realCount / total) * 100).toFixed(1)

  const confBuckets = useMemo(() => {
    const buckets = [
      { label: "50-60%", min: 50, max: 60, count: 0 },
      { label: "60-70%", min: 60, max: 70, count: 0 },
      { label: "70-80%", min: 70, max: 80, count: 0 },
      { label: "80-90%", min: 80, max: 90, count: 0 },
      { label: "90-100%", min: 90, max: 101, count: 0 },
    ]
    filtered.forEach((h: any) => {
      const c = h.confidence || 0
      const b = buckets.find(b => c >= b.min && c < b.max)
      if (b) b.count++
    })
    return buckets
  }, [filtered])

  const topicMap = useMemo(() => {
    const topics: Record<string, { real: number; fake: number }> = {
      "Politics": { real: 0, fake: 0 }, "Health": { real: 0, fake: 0 },
      "Technology": { real: 0, fake: 0 }, "Finance": { real: 0, fake: 0 },
      "Social Media": { real: 0, fake: 0 }, "Other": { real: 0, fake: 0 },
    }
    const rules: [string, RegExp][] = [
      ["Politics", /politic|election|govern|minister|parliament|congress|bjp|aap|vote|democrat|republican/i],
      ["Health", /health|covid|vaccine|hospital|doctor|medical|disease|virus|cure|patient/i],
      ["Technology", /tech|ai|software|google|apple|microsoft|crypto|bitcoin|startup|hack/i],
      ["Finance", /bank|stock|market|invest|rupee|dollar|economy|gdp|inflation|rbi|tax/i],
      ["Social Media", /whatsapp|facebook|instagram|twitter|tiktok|youtube|viral|forward|share/i],
    ]
    filtered.forEach((h: any) => {
      const txt = h.text_preview || h.preview || ""
      const pred = h.prediction === "FAKE" ? "fake" : "real"
      let matched = false
      for (const [topic, re] of rules) {
        if (re.test(txt)) { topics[topic][pred]++; matched = true; break }
      }
      if (!matched) topics["Other"][pred]++
    })
    return Object.entries(topics).filter(([, v]) => v.real + v.fake > 0)
  }, [filtered])

  // Loading guard after all hooks
  if (loading) return <div className="min-h-screen bg-background flex items-center justify-center"><Loader2 className="w-6 h-6 animate-spin text-primary" /></div>

  const greeting = (() => {
    const h = new Date().getHours()
    if (h < 12) return "Good morning"
    if (h < 17) return "Good afternoon"
    return "Good evening"
  })()

  const viewProps: DashboardViewProps = {
    user, greeting, totalAnalyzed, fakeCount, realCount, avgConf,
    fakePercent, realPercent, total, confBuckets, topicMap,
    allHistory, filtered, range, setRange, community
  }

  return isMobile ? <DashboardMobile {...viewProps} /> : <DashboardDesktop {...viewProps} />
}
