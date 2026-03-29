import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { analyzeText } from "../api/analyze";

export default function Analyze() {
  const [inputText, setInputText] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleAnalyze = async () => {
    if (!inputText.trim()) return;
    setLoading(true);
    setResult(null);
    setError(null);
    try {
      const data = await analyzeText(inputText);
      setResult(data);
    } catch (err) {
      setError(
        err.response?.data?.detail ||
          "Something went wrong. Please make sure the backend server is running and try again."
      );
    } finally {
      setLoading(false);
    }
  };

  const isReal = result?.prediction === "REAL";
  const confidencePercent = result
    ? (result.confidence * 100).toFixed(1)
    : null;

  return (
    <section
      id="analyze"
      className="min-h-screen flex flex-col items-center justify-center px-6 py-20"
    >
      {/* Section heading */}
      <motion.h2
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.6 }}
        className="text-3xl md:text-4xl font-bold text-center mb-10 bg-gradient-to-r from-purple-400 to-blue-400 bg-clip-text text-transparent"
      >
        Analyze News
      </motion.h2>

      {/* Card */}
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        whileInView={{ opacity: 1, scale: 1 }}
        viewport={{ once: true }}
        transition={{ duration: 0.5 }}
        className="relative bg-white/5 backdrop-blur-2xl border border-white/10 p-8 rounded-3xl w-full max-w-xl shadow-[0_8px_60px_-12px_rgba(139,92,246,0.25)]"
      >
        {/* Textarea */}
        <textarea
          id="news-input"
          className="w-full p-4 rounded-2xl bg-slate-800/80 text-white placeholder-slate-400 mb-5 resize-none focus:outline-none focus:ring-2 focus:ring-purple-500/50 transition-all duration-300"
          rows="6"
          placeholder="Paste the news article text here..."
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
        />

        {/* Button */}
        <button
          id="analyze-btn"
          onClick={handleAnalyze}
          disabled={loading || !inputText.trim()}
          className="w-full py-3.5 rounded-2xl font-semibold text-white bg-gradient-to-r from-purple-600 to-blue-600 
                     hover:from-purple-500 hover:to-blue-500 hover:shadow-lg hover:shadow-purple-500/25 
                     active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:shadow-none
                     transition-all duration-300 flex items-center justify-center gap-2"
        >
          {loading && (
            <svg
              className="animate-spin h-5 w-5 text-white"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"
              />
            </svg>
          )}
          {loading ? "Analyzing…" : "Analyze"}
        </button>

        {/* Error */}
        <AnimatePresence>
          {error && (
            <motion.div
              key="error"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.3 }}
              className="mt-5 p-4 rounded-2xl bg-red-500/10 border border-red-500/30 text-red-300 text-sm text-center"
            >
              ⚠️ {error}
            </motion.div>
          )}
        </AnimatePresence>

        {/* Result Card */}
        <AnimatePresence>
          {result && (
            <motion.div
              key="result"
              initial={{ opacity: 0, y: 20, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -20, scale: 0.95 }}
              transition={{ type: "spring", stiffness: 300, damping: 24 }}
              className={`mt-6 p-6 rounded-2xl border text-center ${
                isReal
                  ? "bg-emerald-500/10 border-emerald-500/30"
                  : "bg-red-500/10 border-red-500/30"
              }`}
            >
              {/* Icon */}
              <motion.div
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{
                  type: "spring",
                  stiffness: 400,
                  damping: 12,
                  delay: 0.15,
                }}
                className="text-5xl mb-3"
              >
                {isReal ? "✅" : "🚨"}
              </motion.div>

              {/* Prediction label */}
              <motion.p
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.25 }}
                className={`text-2xl font-extrabold tracking-wide ${
                  isReal ? "text-emerald-400" : "text-red-400"
                }`}
              >
                {isReal ? "REAL NEWS" : "FAKE NEWS"}
              </motion.p>

              {/* Confidence bar */}
              <div className="mt-4">
                <p className="text-sm text-slate-400 mb-2">
                  Confidence
                </p>
                <div className="w-full h-3 rounded-full bg-slate-700/60 overflow-hidden">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${confidencePercent}%` }}
                    transition={{ duration: 0.8, ease: "easeOut", delay: 0.3 }}
                    className={`h-full rounded-full ${
                      isReal
                        ? "bg-gradient-to-r from-emerald-500 to-emerald-400"
                        : "bg-gradient-to-r from-red-500 to-red-400"
                    }`}
                  />
                </div>
                <motion.p
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 0.5 }}
                  className={`text-lg font-bold mt-2 ${
                    isReal ? "text-emerald-300" : "text-red-300"
                  }`}
                >
                  {confidencePercent}%
                </motion.p>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    </section>
  );
}