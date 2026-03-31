import { useState, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { analyzeText } from "../api/analyze";
import { addToHistory } from "../utils/history";

/* ── Animation variants ── */
const sectionFade = {
  hidden: { opacity: 0, y: 30 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.7, ease: [0.25, 0.46, 0.45, 0.94] } },
};

const resultCardVariants = {
  hidden: { opacity: 0, scale: 0.8, y: 20 },
  visible: {
    opacity: 1,
    scale: 1,
    y: 0,
    transition: { type: "spring", stiffness: 300, damping: 20, duration: 0.4 },
  },
  exit: { opacity: 0, scale: 0.85, y: -15, transition: { duration: 0.2 } },
};

/* ── Spinner component ── */
function Spinner() {
  return (
    <svg className="animate-spin h-5 w-5 text-white" fill="none" viewBox="0 0 24 24">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
    </svg>
  );
}

/* ── Result style map ── */
function getResultStyle(prediction) {
  if (prediction === "REAL")
    return {
      bg: "bg-emerald-500/[0.07]",
      border: "border-emerald-500/25",
      text: "text-emerald-400",
      bar: "from-emerald-500 to-emerald-400",
      glow: "shadow-emerald-500/15",
      sub: "text-emerald-300",
      icon: "✅",
      label: "REAL NEWS",
      tagline: "This article appears to be credible.",
    };
  if (prediction === "FAKE")
    return {
      bg: "bg-red-500/[0.07]",
      border: "border-red-500/25",
      text: "text-red-400",
      bar: "from-red-500 to-rose-400",
      glow: "shadow-red-500/15",
      sub: "text-red-300",
      icon: "🚨",
      label: "FAKE NEWS",
      tagline: "This article shows signs of misinformation.",
    };
  return {
    bg: "bg-amber-500/[0.07]",
    border: "border-amber-500/25",
    text: "text-amber-400",
    bar: "from-amber-500 to-amber-400",
    glow: "shadow-amber-500/15",
    sub: "text-amber-300",
    icon: "⚠️",
    label: "UNCERTAIN",
    tagline: "The model isn't confident enough to classify this text.",
  };
}

export default function Analyze() {
  const [inputText, setInputText] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const textareaRef = useRef(null);

  const charCount = inputText.length;

  const handleAnalyze = async () => {
    const trimmed = inputText.trim();
    if (!trimmed) return;

    setLoading(true);
    setResult(null);
    setError(null);

    try {
      const data = await analyzeText(trimmed);
      setResult(data);
      addToHistory({
        text: trimmed,
        prediction: data.prediction,
        confidence: data.confidence,
      });
      window.dispatchEvent(new Event("history-updated"));
    } catch (err) {
      setError(
        err.response?.data?.detail ||
          "Something went wrong. Please make sure the backend server is running and try again."
      );
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleAnalyze();
    }
  };

  const handleClear = () => {
    setInputText("");
    setResult(null);
    setError(null);
    textareaRef.current?.focus();
  };

  const prediction = result?.prediction;
  const isUncertain = prediction === "UNCERTAIN";
  const confidencePercent = result ? (result.confidence * 100).toFixed(1) : null;
  const rs = result ? getResultStyle(prediction) : null;

  return (
    <section
      id="analyze"
      className="relative min-h-screen flex flex-col items-center justify-center px-6 py-24"
    >
      {/* ── Section heading ── */}
      <motion.div
        variants={sectionFade}
        initial="hidden"
        whileInView="visible"
        viewport={{ once: true, margin: "-80px" }}
        className="text-center mb-10"
      >
        <span className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full text-xs font-medium tracking-wide bg-purple-500/10 text-purple-300 border border-purple-500/20 mb-5">
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M9.75 3.104v5.714a2.25 2.25 0 0 1-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 0 1 4.5 0m0 0v5.714a2.25 2.25 0 0 0 .659 1.591L19 14.5" />
          </svg>
          AI Analysis Engine
        </span>
        <h2 className="text-3xl md:text-4xl font-bold bg-gradient-to-r from-purple-400 via-violet-400 to-blue-400 bg-clip-text text-transparent">
          Analyze News Article
        </h2>
        <p className="text-slate-400 text-sm md:text-base mt-3 max-w-md mx-auto">
          Paste any news text below and let our ML model determine its authenticity in seconds.
        </p>
      </motion.div>

      {/* ── Main glassmorphism card ── */}
      <motion.div
        variants={sectionFade}
        initial="hidden"
        whileInView="visible"
        viewport={{ once: true, margin: "-50px" }}
        className="relative w-full max-w-2xl"
      >
        {/* Ambient glow behind card */}
        <div
          className="absolute -inset-4 rounded-[2rem] opacity-40 blur-3xl pointer-events-none -z-10"
          style={{
            background:
              "radial-gradient(ellipse at 30% 20%, rgba(139,92,246,0.15), transparent 60%), radial-gradient(ellipse at 70% 80%, rgba(59,130,246,0.12), transparent 60%)",
          }}
          aria-hidden="true"
        />

        <div className="bg-white/[0.04] backdrop-blur-2xl border border-white/[0.08] rounded-3xl p-8 md:p-10 shadow-[0_8px_60px_-12px_rgba(139,92,246,0.22),0_0_0_1px_rgba(255,255,255,0.03)]">
          {/* ── Textarea ── */}
          <div className="relative">
            <textarea
              ref={textareaRef}
              id="news-input"
              className="w-full p-5 rounded-2xl bg-slate-800/70 text-white text-[15px] placeholder-slate-500 resize-none
                         border border-white/[0.06]
                         focus:outline-none focus:ring-2 focus:ring-purple-500/40 focus:border-purple-500/30
                         transition-all duration-300 leading-relaxed"
              rows="6"
              placeholder="Paste the news article text here..."
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={loading}
            />

            {/* Character count + clear */}
            <div className="flex items-center justify-between mt-2.5 px-1">
              <span className={`text-xs font-mono transition-colors duration-300 ${charCount > 0 ? "text-slate-400" : "text-slate-600"}`}>
                {charCount > 0 ? `${charCount.toLocaleString()} chars` : "0 chars"}
              </span>
              {charCount > 0 && (
                <button
                  onClick={handleClear}
                  className="text-xs text-slate-500 hover:text-slate-300 transition-colors duration-200 flex items-center gap-1"
                >
                  <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                  Clear
                </button>
              )}
            </div>
          </div>

          {/* ── Analyze button ── */}
          <button
            id="analyze-btn"
            onClick={handleAnalyze}
            disabled={loading || !inputText.trim()}
            className="group relative w-full mt-5 py-3.5 rounded-2xl font-semibold text-white
                       bg-gradient-to-r from-purple-600 via-violet-600 to-blue-600
                       hover:from-purple-500 hover:via-violet-500 hover:to-blue-500
                       hover:shadow-[0_0_30px_rgba(139,92,246,0.35)] hover:scale-[1.02]
                       active:scale-[0.98]
                       disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:shadow-none disabled:hover:scale-100
                       transition-all duration-300 ease-out
                       flex items-center justify-center gap-2.5 overflow-hidden"
          >
            {/* Shimmer sweep */}
            {!loading && (
              <span className="absolute inset-0 bg-gradient-to-r from-transparent via-white/[0.08] to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-700 ease-in-out" aria-hidden="true" />
            )}

            {loading && <Spinner />}
            <span className="relative">
              {loading ? "Analyzing…" : "Analyze"}
            </span>

            {!loading && (
              <svg
                className="relative w-4 h-4 transition-transform duration-300 group-hover:translate-x-0.5"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2.5}
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M13 7l5 5m0 0l-5 5m5-5H6" />
              </svg>
            )}
          </button>




          {/* ── Error state ── */}
          <AnimatePresence>
            {error && (
              <motion.div
                key="error"
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                transition={{ duration: 0.3 }}
                className="mt-5 p-4 rounded-2xl bg-red-500/[0.08] border border-red-500/25 text-red-300 text-sm text-center flex items-center justify-center gap-2"
              >
                <svg className="w-4 h-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z" />
                </svg>
                {error}
              </motion.div>
            )}
          </AnimatePresence>

          {/* ── Result card ── */}
          <AnimatePresence>
            {result && rs && (
              <motion.div
                key="result"
                variants={resultCardVariants}
                initial="hidden"
                animate="visible"
                exit="exit"
                className={`mt-6 rounded-2xl border overflow-hidden ${rs.bg} ${rs.border} shadow-lg ${rs.glow}`}
              >
                {/* Result header */}
                <div className="p-6 pb-4 text-center">
                  {/* Icon */}
                  <motion.div
                    initial={{ scale: 0, rotate: -20 }}
                    animate={{ scale: 1, rotate: 0 }}
                    transition={{ type: "spring", stiffness: 400, damping: 14, delay: 0.12 }}
                    className="text-5xl mb-3"
                  >
                    {rs.icon}
                  </motion.div>

                  {/* Label */}
                  <motion.p
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.2 }}
                    className={`text-2xl font-extrabold tracking-wide ${rs.text}`}
                  >
                    {rs.label}
                  </motion.p>

                  {/* Tagline */}
                  <motion.p
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.3 }}
                    className="text-sm text-slate-400 mt-1.5"
                  >
                    {rs.tagline}
                  </motion.p>
                </div>

                {/* Confidence section */}
                {!isUncertain && (
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.35 }}
                    className="px-6 pb-6"
                  >
                    <div className="bg-slate-900/40 rounded-xl p-4 border border-white/[0.04]">
                      <div className="flex items-center justify-between mb-3">
                        <span className="text-xs uppercase tracking-widest text-slate-500 font-medium">
                          Confidence Score
                        </span>
                        <motion.span
                          initial={{ opacity: 0, scale: 0.8 }}
                          animate={{ opacity: 1, scale: 1 }}
                          transition={{ delay: 0.5 }}
                          className={`text-lg font-bold ${rs.sub}`}
                        >
                          {confidencePercent}%
                        </motion.span>
                      </div>

                      {/* Progress bar */}
                      <div className="w-full h-2.5 rounded-full bg-slate-700/50 overflow-hidden">
                        <motion.div
                          initial={{ width: 0 }}
                          animate={{ width: `${confidencePercent}%` }}
                          transition={{ duration: 1, ease: [0.25, 0.46, 0.45, 0.94], delay: 0.4 }}
                          className={`h-full rounded-full bg-gradient-to-r ${rs.bar}`}
                        />
                      </div>

                      {/* Scale markers */}
                      <div className="flex justify-between mt-1.5">
                        <span className="text-[10px] text-slate-600">0%</span>
                        <span className="text-[10px] text-slate-600">50%</span>
                        <span className="text-[10px] text-slate-600">100%</span>
                      </div>
                    </div>
                  </motion.div>
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </motion.div>
    </section>
  );
}