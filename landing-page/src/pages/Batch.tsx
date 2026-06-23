import { useState, useRef } from "react"
import { useAuth } from "../context/AuthContext"
import { API_BASE, getAuthHeaders } from "../lib/api"
import { Loader2, Download, FileSpreadsheet } from "lucide-react"
import { Button } from "../components/ui/button"

export function BatchPage() {
  const { user } = useAuth()
  const [file, setFile] = useState<File | null>(null)
  const [processing, setProcessing] = useState(false)
  const [progress, setProgress] = useState(0)
  const [results, setResults] = useState<any[]>([])
  const [error, setError] = useState("")
  const dropRef = useRef<HTMLDivElement>(null)

  if (!user) return <div className="min-h-screen bg-background flex items-center justify-center text-foreground"><p>Please sign in.</p></div>

  const [fileInfo, setFileInfo] = useState<{ rows: number; cols: string[]; samples: string[]; textCol: string } | null>(null)

  const handleFile = (f: File) => {
    if (!f.name.endsWith(".csv")) { setError("Only .csv files accepted."); return }
    setFile(f); setError(""); setResults([]); setFileInfo(null)
    // parse preview
    f.text().then(text => {
      const lines = text.split("\n").filter(l => l.trim())
      const cols = lines[0].split(",").map(c => c.trim())
      const textCol = cols.find(c => c.toLowerCase() === "text" || c.toLowerCase() === "content") || ""
      const colIdx = cols.findIndex(c => c.toLowerCase() === "text" || c.toLowerCase() === "content")
      const samples = lines.slice(1, 4).map(l => {
        const parts = l.split(",")
        return colIdx >= 0 ? parts.slice(colIdx).join(",").replace(/^"|"$/g, "").trim().slice(0, 100) : l.slice(0, 100)
      })
      setFileInfo({ rows: lines.length - 1, cols, samples, textCol })
    })
  }

  const startBatch = async () => {
    if (!file) return
    setProcessing(true); setProgress(0); setResults([]); setError("")
    try {
      const text = await file.text()
      const lines = text.split("\n").filter(l => l.trim())
      const header = lines[0].toLowerCase()
      const colIdx = header.split(",").findIndex(c => c.trim() === "text" || c.trim() === "content")
      if (colIdx < 0) { setError("CSV must have a 'text' or 'content' column."); setProcessing(false); return }

      const rows = lines.slice(1).slice(0, 500)
      const batchResults: any[] = []
      for (let i = 0; i < rows.length; i++) {
        const cols = rows[i].split(",")
        const content = cols.slice(colIdx).join(",").replace(/^"|"$/g, "").trim()
        if (!content) continue
        try {
          const res = await fetch(`${API_BASE}/api/v1/analyze`, {
            method: "POST", headers: getAuthHeaders(),
            body: JSON.stringify({ text: content })
          })
          const data = await res.json()
          batchResults.push({ preview: content.slice(0, 80), ...data })
        } catch {
          batchResults.push({ preview: content.slice(0, 80), prediction: "ERROR", confidence: 0 })
        }
        setProgress(Math.round(((i + 1) / rows.length) * 100))
      }
      setResults(batchResults)
    } catch (e: any) { setError(e.message) }
    finally { setProcessing(false) }
  }

  const downloadCsv = () => {
    const header = "Preview,Prediction,Confidence,Real_Prob,Fake_Prob,Red_Flags\n"
    const rows = results.map(r =>
      `"${r.preview?.replace(/"/g, '""')}",${r.prediction},${r.confidence?.toFixed(1) ?? 0},${((r.real_probability ?? 0) * 100).toFixed(1)},${((r.fake_probability ?? 0) * 100).toFixed(1)},${r.red_flag_score ?? 0}`
    ).join("\n")
    const blob = new Blob([header + rows], { type: "text/csv" })
    const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = "verifai-batch-results.csv"; a.click()
  }

  return (
    <div className="bg-background p-6 md:p-8 text-foreground">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold tracking-tight mb-2">Bulk Analysis</h1>
        <p className="text-muted-foreground text-sm mb-8">Upload a CSV with a 'text' or 'content' column to analyze multiple articles at once.</p>

        {/* Upload zone */}
        <div ref={dropRef}
          onDragOver={e => { e.preventDefault(); dropRef.current?.classList.add("border-primary") }}
          onDragLeave={() => dropRef.current?.classList.remove("border-primary")}
          onDrop={e => { e.preventDefault(); dropRef.current?.classList.remove("border-primary"); e.dataTransfer.files[0] && handleFile(e.dataTransfer.files[0]) }}
          className="border-2 border-dashed border-border rounded-xl p-10 text-center bg-secondary hover:border-primary/50 transition-colors cursor-pointer mb-6"
          onClick={() => { const inp = document.createElement("input"); inp.type = "file"; inp.accept = ".csv"; inp.onchange = (e: any) => e.target.files[0] && handleFile(e.target.files[0]); inp.click() }}>
          <FileSpreadsheet className="w-10 h-10 text-muted-foreground mx-auto mb-3" />
          <p className="text-sm text-foreground font-medium">Drag & drop a CSV file, or click to browse</p>
          <p className="text-xs text-muted-foreground mt-1">Maximum 500 rows. Accepted: .csv</p>
        </div>

        {file && !processing && results.length === 0 && (
          <div className="bg-secondary border border-border rounded-xl p-5 mb-6 space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <FileSpreadsheet className="w-5 h-5 text-primary" />
                <div>
                  <p className="text-sm font-medium text-foreground">{file.name}</p>
                  <p className="text-[11px] text-muted-foreground">
                    {(file.size / 1024).toFixed(1)} KB
                    {fileInfo && <> · {fileInfo.rows} rows · {fileInfo.cols.length} columns</>}
                  </p>
                </div>
              </div>
              <Button onClick={startBatch} disabled={!fileInfo?.textCol}>Start Batch Analysis</Button>
            </div>
            {fileInfo && (
              <>
                <div className="flex items-center gap-2 text-xs">
                  <span className={`w-2 h-2 rounded-full ${fileInfo.textCol ? 'bg-[#4ADE80]' : 'bg-destructive'}`} />
                  <span className="text-muted-foreground">
                    {fileInfo.textCol
                      ? <>Text column detected: <span className="text-foreground font-medium">"{fileInfo.textCol}"</span></>
                      : <span className="text-destructive">No 'text' or 'content' column found</span>}
                  </span>
                </div>
                {fileInfo.samples.length > 0 && (
                  <div>
                    <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-2">Sample rows</p>
                    <div className="space-y-1.5">
                      {fileInfo.samples.map((s, i) => (
                        <div key={i} className="bg-background rounded-lg px-3 py-2 text-[11px] text-muted-foreground truncate">{s || "—"}</div>
                      ))}
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        )}

        {error && <p className="text-destructive text-sm mb-4">{error}</p>}

        {processing && (
          <div className="mb-6">
            <div className="h-2 w-full bg-background rounded-full overflow-hidden mb-2">
              <div className="h-full bg-primary transition-all duration-300" style={{ width: `${progress}%` }} />
            </div>
            <p className="text-xs text-muted-foreground flex items-center gap-2"><Loader2 className="w-3 h-3 animate-spin" /> Processing... {progress}%</p>
          </div>
        )}

        {results.length > 0 && (
          <div className="bg-secondary border border-border rounded-xl overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead><tr className="border-b border-border bg-background/50">
                  <th className="text-left p-3 text-xs text-muted-foreground font-medium">Preview</th>
                  <th className="text-left p-3 text-xs text-muted-foreground font-medium">Prediction</th>
                  <th className="text-left p-3 text-xs text-muted-foreground font-medium">Confidence</th>
                  <th className="text-left p-3 text-xs text-muted-foreground font-medium">Red Flags</th>
                </tr></thead>
                <tbody>
                  {results.map((r, i) => (
                    <tr key={i} className="border-b border-border/50 hover:bg-background/30">
                      <td className="p-3 text-xs max-w-[200px] truncate">{r.preview}</td>
                      <td className="p-3"><span className={`text-xs font-medium px-2 py-0.5 rounded-full ${r.prediction === "FAKE" ? "bg-destructive/15 text-destructive" : r.prediction === "REAL" ? "bg-[#4ADE80]/15 text-[#4ADE80]" : "bg-muted text-muted-foreground"}`}>{r.prediction}</span></td>
                      <td className="p-3 text-xs">{r.confidence?.toFixed(1) ?? 0}%</td>
                      <td className="p-3 text-xs">{r.red_flag_score ?? 0}/10</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="p-4 border-t border-border">
              <Button onClick={downloadCsv} variant="outline" size="sm"><Download className="w-4 h-4 mr-2" /> Download Results CSV</Button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
