import { useState, useRef } from "react"
import { useAuth } from "../context/AuthContext"
import { API_BASE, getAuthHeaders } from "../lib/api"
import { FileText, Link as LinkIcon, Mic, Upload, CheckCircle2, AlertTriangle, ShieldAlert, FileAudio } from "lucide-react"
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
    await analyzeData("/api/v1/analyze", { text: inputText });
  };

  const handleAnalyzeUrl = async () => {
    if (!inputUrl.trim()) { setError("Please enter a URL."); return; }
    await analyzeData("/api/v1/analyze-url", { url: inputUrl });
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
      await analyzeData("/api/v1/analyze", { text: data.text });
      
    } catch (err: any) {
      setError(err.message);
      setLoading(false);
    }
  };

  const analyzeData = async (endpoint: string, body: any) => {
    setError("");
    setLoading(true);
    setResult(null);
    try {
      const res = await fetch(`${API_BASE}${endpoint}`, {
        method: "POST",
        headers: getAuthHeaders(),
        body: JSON.stringify(body)
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
                      {loading ? "Analyzing..." : "Analyze Content"}
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
                      {loading ? "Fetching & Analyzing..." : "Analyze URL"}
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
                      <Upload className="w-4 h-4 mr-2" />
                      {loading ? "Processing Audio..." : "Select Audio File"}
                    </Button>
                  </div>
                )}

                {error && (
                  <div className="mt-4 p-3 bg-destructive/10 border border-destructive/30 text-destructive text-sm rounded-lg flex items-start gap-2">
                    <AlertTriangle className="w-5 h-5 shrink-0" />
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
                      Confidence: {(result.confidence * 100).toFixed(1)}%
                    </p>
                  </div>
                </div>

                <div className="space-y-5">
                  <div>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-muted-foreground">Fake Probability</span>
                      <span className="font-medium">{(result.probabilities.FAKE * 100).toFixed(1)}%</span>
                    </div>
                    <div className="h-2 w-full bg-background rounded-full overflow-hidden">
                      <div className="h-full bg-destructive" style={{ width: `${result.probabilities.FAKE * 100}%` }} />
                    </div>
                  </div>
                  <div>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-muted-foreground">Real Probability</span>
                      <span className="font-medium">{(result.probabilities.REAL * 100).toFixed(1)}%</span>
                    </div>
                    <div className="h-2 w-full bg-background rounded-full overflow-hidden">
                      <div className="h-full bg-[#4ADE80]" style={{ width: `${result.probabilities.REAL * 100}%` }} />
                    </div>
                  </div>
                  <div>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-muted-foreground">Red Flag Severity</span>
                      <span className="font-medium">{result.red_flag_score}/10</span>
                    </div>
                    <div className="h-2 w-full bg-background rounded-full overflow-hidden">
                      <div className="h-full bg-accent" style={{ width: `${(result.red_flag_score / 10) * 100}%` }} />
                    </div>
                  </div>
                </div>

                {result.india_threat_scan && result.india_threat_scan.threat_detected && (
                  <div className="mt-6 p-4 bg-primary/10 border border-primary/30 rounded-lg">
                    <h4 className="text-sm font-bold text-primary mb-1 uppercase tracking-wider">⚠️ Threat Detected</h4>
                    <p className="text-xs text-foreground/90">
                      Category: <span className="font-semibold">{result.india_threat_scan.primary_category}</span>
                    </p>
                    <p className="text-xs text-muted-foreground mt-1">
                      Our system detected {result.india_threat_scan.matched_keywords.length} suspicious keywords common in local scams.
                    </p>
                  </div>
                )}
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
