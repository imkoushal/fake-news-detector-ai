import { useState, useRef } from "react"
import { useAuth } from "../context/AuthContext"
import { API_BASE, getAuthHeaders } from "../lib/api"
import { FileText, Link as LinkIcon, Mic, Upload, CheckCircle2, AlertTriangle, ShieldAlert, FileAudio, Loader2 } from "lucide-react"
import { Button } from "../components/ui/button"

export function Dashboard() {
  const { user, logout, token } = useAuth();
  
  const [activeTab, setActiveTab] = useState<"text" | "url" | "audio">("text");
  const [inputText, setInputText] = useState("");
  const [inputUrl, setInputUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<any>(null);
  
  const fileInputRef = useRef<HTMLInputElement>(null);

  if (!user) return (
    <div className="min-h-screen bg-background flex items-center justify-center text-foreground">
      <p>Please sign in to view the dashboard.</p>
    </div>
  );

  const handleAnalyzeText = async () => {
    if (!inputText.trim()) { setError("Please enter some text."); return; }
    await analyzeData(inputText);
  };

  const handleAnalyzeUrl = async () => {
    if (!inputUrl.trim()) { setError("Please enter a URL."); return; }
    setError("");
    setLoading(true);
    setResult(null);

    try {
      // Step 1: Fetch article text from URL via the backend
      const fetchRes = await fetch(`${API_BASE}/api/v1/fetch-url`, {
        method: "POST",
        headers: getAuthHeaders(),
        body: JSON.stringify({ url: inputUrl })
      });
      const fetchData = await fetchRes.json();
      if (!fetchRes.ok) throw new Error(fetchData.detail || "Failed to fetch URL content");
      if (!fetchData.text || fetchData.text.trim().length < 10) {
        throw new Error("Could not extract enough text from that URL. Try pasting the article text directly.");
      }

      // Step 2: Analyze the extracted text
      setInputText(fetchData.text);
      await analyzeData(fetchData.text);
    } catch (err: any) {
      setError(err.message);
      setLoading(false);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.size > 25 * 1024 * 1024) { setError("File too large. Max 25MB."); return; }

    setError("");
    setLoading(true);
    setResult(null);

    const formData = new FormData();
    formData.append("file", file);

    try {
      // 1. Transcribe
      const res = await fetch(`${API_BASE}/api/v1/transcribe`, {
        method: "POST",
        headers: token ? { "Authorization": `Bearer ${token}` } : {},
        body: formData
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Transcription failed");
      if (!data.text) throw new Error("No speech detected.");

      // 2. Analyze the transcribed text
      setInputText(data.text);
      setActiveTab("text");
      await analyzeData(data.text);
      
    } catch (err: any) {
      setError(err.message);
      setLoading(false);
    }

    // Reset file input so the same file can be re-selected
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const analyzeData = async (text: string) => {
    setError("");
    setLoading(true);
    setResult(null);
    try {
      const res = await fetch(`${API_BASE}/api/v1/analyze`, {
        method: "POST",
        headers: getAuthHeaders(),
        body: JSON.stringify({ text })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Analysis failed");
      setResult(data);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background pt-24 px-6 md:px-12 lg:px-20 text-foreground pb-20">
      <div className="max-w-5xl mx-auto">
        <div className="flex justify-between items-center mb-10">
          <div>
            <h1 className="text-3xl font-bold tracking-tight mb-1">Dashboard</h1>
            <p className="text-muted-foreground text-sm">Welcome back, {user.name}</p>
          </div>
          <Button variant="outline" size="sm" onClick={logout}>Sign Out</Button>
        </div>
        
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          {/* Input Section */}
          <div className="lg:col-span-7 flex flex-col gap-6">
            <div className="bg-secondary rounded-xl border border-border overflow-hidden shadow-sm">
              <div className="flex border-b border-border bg-background/50">
                <button 
                  onClick={() => setActiveTab("text")}
                  className={`flex-1 py-3 text-sm font-medium flex items-center justify-center gap-2 transition-colors ${activeTab === 'text' ? 'bg-secondary text-primary border-b-2 border-primary' : 'text-muted-foreground hover:text-foreground'}`}
                >
                  <FileText className="w-4 h-4" /> Text
                </button>
                <button 
                  onClick={() => setActiveTab("url")}
                  className={`flex-1 py-3 text-sm font-medium flex items-center justify-center gap-2 transition-colors ${activeTab === 'url' ? 'bg-secondary text-primary border-b-2 border-primary' : 'text-muted-foreground hover:text-foreground'}`}
                >
                  <LinkIcon className="w-4 h-4" /> URL
                </button>
                <button 
                  onClick={() => setActiveTab("audio")}
                  className={`flex-1 py-3 text-sm font-medium flex items-center justify-center gap-2 transition-colors ${activeTab === 'audio' ? 'bg-secondary text-primary border-b-2 border-primary' : 'text-muted-foreground hover:text-foreground'}`}
                >
                  <Mic className="w-4 h-4" /> Audio
                </button>
              </div>

              <div className="p-6">
                {activeTab === "text" && (
                  <div className="animate-fade-in">
                    <textarea 
                      placeholder="Paste the news article or social media post here..."
                      className="w-full h-48 bg-background border border-border rounded-lg p-4 text-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 resize-none mb-4"
                      value={inputText}
                      onChange={e => setInputText(e.target.value)}
                    />
                    <Button className="w-full" size="lg" onClick={handleAnalyzeText} disabled={loading}>
                      {loading ? (
                        <span className="flex items-center gap-2">
                          <Loader2 className="w-4 h-4 animate-spin" /> Analyzing...
                        </span>
                      ) : "Analyze Content"}
                    </Button>
                  </div>
                )}

                {activeTab === "url" && (
                  <div className="animate-fade-in space-y-4">
                    <input 
                      type="url"
                      placeholder="https://example.com/news-article"
                      className="w-full bg-background border border-border rounded-lg px-4 py-3 text-foreground focus:outline-none focus:ring-2 focus:ring-primary/50"
                      value={inputUrl}
                      onChange={e => setInputUrl(e.target.value)}
                    />
                    <Button className="w-full" size="lg" onClick={handleAnalyzeUrl} disabled={loading}>
                      {loading ? (
                        <span className="flex items-center gap-2">
                          <Loader2 className="w-4 h-4 animate-spin" /> Fetching & Analyzing...
                        </span>
                      ) : "Analyze URL"}
                    </Button>
                  </div>
                )}

                {activeTab === "audio" && (
                  <div className="animate-fade-in text-center py-8">
                    <div className="w-16 h-16 bg-primary/10 rounded-full flex items-center justify-center mx-auto mb-4 text-primary">
                      <FileAudio className="w-8 h-8" />
                    </div>
                    <h3 className="text-lg font-medium mb-2">Upload Audio Note</h3>
                    <p className="text-sm text-muted-foreground mb-6 max-w-sm mx-auto">
                      Upload a WhatsApp voice note or audio file. Our AI will transcribe and analyze it automatically.
                    </p>
                    <input 
                      type="file" 
                      accept="audio/*" 
                      className="hidden" 
                      ref={fileInputRef}
                      onChange={handleFileUpload}
                    />
                    <Button variant="outline" size="lg" onClick={() => fileInputRef.current?.click()} disabled={loading}>
                      {loading ? (
                        <span className="flex items-center gap-2">
                          <Loader2 className="w-4 h-4 animate-spin" /> Processing Audio...
                        </span>
                      ) : (
                        <span className="flex items-center gap-2">
                          <Upload className="w-4 h-4" /> Select Audio File
                        </span>
                      )}
                    </Button>
                  </div>
                )}

                {error && (
                  <div className="mt-4 p-3 bg-destructive/10 border border-destructive/30 text-destructive text-sm rounded-lg flex items-start gap-2">
                    <AlertTriangle className="w-5 h-5 shrink-0 mt-0.5" />
                    <p>{error}</p>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Results Section */}
          <div className="lg:col-span-5">
            {result ? (
              <div className="bg-secondary rounded-xl border border-border p-6 shadow-sm animate-fade-up">
                <div className="flex items-center gap-3 mb-6">
                  {result.prediction === "FAKE" ? (
                    <ShieldAlert className="w-8 h-8 text-destructive" />
                  ) : (
                    <CheckCircle2 className="w-8 h-8 text-[#4ADE80]" />
                  )}
                  <div>
                    <h2 className="text-xl font-bold uppercase tracking-wide">
                      {result.prediction}
                    </h2>
                    <p className="text-xs text-muted-foreground">
                      {result.confidence_tier} · {result.confidence.toFixed(1)}% confidence
                    </p>
                  </div>
                </div>

                <div className="space-y-5">
                  <div>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-muted-foreground">Fake Probability</span>
                      <span className="font-medium">{(result.fake_probability * 100).toFixed(1)}%</span>
                    </div>
                    <div className="h-2 w-full bg-background rounded-full overflow-hidden">
                      <div className="h-full bg-destructive transition-all duration-500" style={{ width: `${result.fake_probability * 100}%` }} />
                    </div>
                  </div>
                  <div>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-muted-foreground">Real Probability</span>
                      <span className="font-medium">{(result.real_probability * 100).toFixed(1)}%</span>
                    </div>
                    <div className="h-2 w-full bg-background rounded-full overflow-hidden">
                      <div className="h-full bg-[#4ADE80] transition-all duration-500" style={{ width: `${result.real_probability * 100}%` }} />
                    </div>
                  </div>
                  <div>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-muted-foreground">Red Flag Severity</span>
                      <span className="font-medium">{result.red_flag_score}/10</span>
                    </div>
                    <div className="h-2 w-full bg-background rounded-full overflow-hidden">
                      <div className="h-full bg-accent transition-all duration-500" style={{ width: `${(result.red_flag_score / 10) * 100}%` }} />
                    </div>
                  </div>
                </div>

                {/* Indicator Words */}
                {(result.fake_indicator_words?.length > 0 || result.real_indicator_words?.length > 0) && (
                  <div className="mt-6 pt-5 border-t border-border">
                    <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">Key Indicator Words</h4>
                    <div className="flex flex-wrap gap-1.5">
                      {result.fake_indicator_words?.slice(0, 5).map((w: string, i: number) => (
                        <span key={`f-${i}`} className="text-xs bg-destructive/15 text-destructive px-2 py-0.5 rounded-full">{w}</span>
                      ))}
                      {result.real_indicator_words?.slice(0, 5).map((w: string, i: number) => (
                        <span key={`r-${i}`} className="text-xs bg-[#4ADE80]/15 text-[#4ADE80] px-2 py-0.5 rounded-full">{w}</span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Input Quality Warning */}
                {result.input_quality !== "sufficient" && (
                  <div className="mt-4 p-3 bg-accent/10 border border-accent/30 rounded-lg">
                    <p className="text-xs text-accent font-medium">
                      ⚠️ {result.input_quality === "short_claim" ? "Very short input — confidence is capped at 60%." : "Short headline — confidence is capped at 80%."}
                      For best results, paste the full article.
                    </p>
                  </div>
                )}

                {/* Model Info */}
                <div className="mt-4 text-[11px] text-muted-foreground/50">
                  Model v{result.model_version} · {result.timestamp?.split("T")[0]}
                </div>
              </div>
            ) : (
              <div className="bg-background border border-border border-dashed rounded-xl p-8 flex flex-col items-center justify-center text-center h-full min-h-[300px]">
                <ShieldAlert className="w-12 h-12 text-muted mb-4" />
                <h3 className="text-foreground font-medium mb-1">No Analysis Yet</h3>
                <p className="text-muted-foreground text-sm max-w-[200px]">
                  Submit text, a URL, or an audio file to see the AI verification results here.
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
