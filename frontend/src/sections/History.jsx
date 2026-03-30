import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { getHistory, clearHistory } from "../utils/history";

export default function History() {
  const [history, setHistory] = useState([]);

  useEffect(() => {
    setHistory(getHistory());

    const handleUpdate = () => setHistory(getHistory());
    window.addEventListener("history-updated", handleUpdate);
    return () => window.removeEventListener("history-updated", handleUpdate);
  }, []);

  const handleClear = () => {
    clearHistory();
    setHistory([]);
  };

  const formatTime = (iso) => {
    const d = new Date(iso);
    return d.toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const truncate = (str, len = 80) =>
    str.length > len ? str.slice(0, len) + "…" : str;

  return (
    <section
      id="history"
      className="min-h-screen flex flex-col items-center px-6 py-24"
    >
      {/* Heading */}
      <motion.h2
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.6 }}
        className="text-3xl md:text-4xl font-bold text-center mb-4 bg-gradient-to-r from-purple-400 to-blue-400 bg-clip-text text-transparent"
      >
        Analysis History
      </motion.h2>

      <motion.p
        initial={{ opacity: 0 }}
        whileInView={{ opacity: 1 }}
        viewport={{ once: true }}
        transition={{ delay: 0.2 }}
        className="text-slate-400 text-center mb-10 max-w-md"
      >
        Your recent analysis results, stored locally on your device.
      </motion.p>

      {/* Empty state */}
      {history.length === 0 && (
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          className="bg-white/5 backdrop-blur-2xl border border-white/10 rounded-3xl p-12 text-center max-w-md w-full"
        >
          <p className="text-5xl mb-4">📭</p>
          <p className="text-slate-400 text-lg">No history yet</p>
          <p className="text-slate-500 text-sm mt-1">
            Analyze some news articles and they'll appear here.
          </p>
        </motion.div>
      )}

      {/* History cards */}
      {history.length > 0 && (
        <div className="w-full max-w-3xl">
          <div className="grid gap-4">
            <AnimatePresence>
              {history.map((item, i) => {
                const isReal = item.prediction === "REAL";
                const isFake = item.prediction === "FAKE";
                const isUncertain = item.prediction === "UNCERTAIN";
                const confidence = (item.confidence * 100).toFixed(1);

                const badgeClass = isReal
                  ? "bg-emerald-500/15 text-emerald-400 border border-emerald-500/30"
                  : isFake
                  ? "bg-red-500/15 text-red-400 border border-red-500/30"
                  : "bg-amber-500/15 text-amber-400 border border-amber-500/30";

                const badgeText = isReal ? "✅ REAL" : isFake ? "🚨 FAKE" : "⚠️ UNCERTAIN";

                const barClass = isReal
                  ? "bg-gradient-to-r from-emerald-500 to-emerald-400"
                  : isFake
                  ? "bg-gradient-to-r from-red-500 to-red-400"
                  : "bg-gradient-to-r from-amber-500 to-amber-400";

                return (
                  <motion.div
                    key={item.timestamp + i}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -20 }}
                    transition={{ duration: 0.35, delay: i * 0.05 }}
                    whileHover={{ scale: 1.015 }}
                    className="group bg-white/5 backdrop-blur-2xl border border-white/10 rounded-2xl p-5 
                               shadow-lg hover:shadow-purple-500/10 transition-all duration-300 cursor-default"
                  >
                    <div className="flex items-start justify-between gap-4">
                      {/* Left: text + time */}
                      <div className="flex-1 min-w-0">
                        <p className="text-white/90 text-sm leading-relaxed mb-2">
                          {truncate(item.text)}
                        </p>
                        <p className="text-slate-500 text-xs">
                          {formatTime(item.timestamp)}
                        </p>
                      </div>

                      {/* Right: prediction badge + confidence */}
                      <div className="flex flex-col items-end gap-1.5 shrink-0">
                        <span
                          className={`px-3 py-1 rounded-full text-xs font-bold tracking-wide ${badgeClass}`}
                        >
                          {badgeText}
                        </span>
                        {!isUncertain && (
                          <span className="text-slate-400 text-xs font-medium">
                            {confidence}%
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Confidence bar */}
                    {!isUncertain && (
                      <div className="mt-3 w-full h-1.5 rounded-full bg-slate-700/50 overflow-hidden">
                        <motion.div
                          initial={{ width: 0 }}
                          whileInView={{ width: `${confidence}%` }}
                          viewport={{ once: true }}
                          transition={{ duration: 0.6, delay: i * 0.05 + 0.2 }}
                          className={`h-full rounded-full ${barClass}`}
                        />
                      </div>
                    )}
                  </motion.div>
                );
              })}
            </AnimatePresence>
          </div>

          {/* Clear button */}
          <motion.div
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            transition={{ delay: 0.3 }}
            className="flex justify-center mt-8"
          >
            <button
              id="clear-history-btn"
              onClick={handleClear}
              className="px-6 py-2.5 rounded-xl text-sm font-medium text-red-400 
                         bg-red-500/10 border border-red-500/20 
                         hover:bg-red-500/20 hover:border-red-500/40 
                         active:scale-95 transition-all duration-300"
            >
              🗑️ Clear History
            </button>
          </motion.div>
        </div>
      )}
    </section>
  );
}
