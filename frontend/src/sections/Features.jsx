export default function Features() {
  return (
    <section id="features" className="min-h-screen flex items-center justify-center px-6">

      <div className="grid md:grid-cols-3 gap-6 max-w-5xl">

        <div className="bg-white/10 backdrop-blur-xl p-6 rounded-2xl border border-white/20 text-center">
          <h2 className="text-xl font-bold mb-2">⚡ Fast Detection</h2>
          <p className="text-gray-400">Analyze news instantly with optimized ML models.</p>
        </div>

        <div className="bg-white/10 backdrop-blur-xl p-6 rounded-2xl border border-white/20 text-center">
          <h2 className="text-xl font-bold mb-2">🧠 AI Powered</h2>
          <p className="text-gray-400">Uses NLP and machine learning for accuracy.</p>
        </div>

        <div className="bg-white/10 backdrop-blur-xl p-6 rounded-2xl border border-white/20 text-center">
          <h2 className="text-xl font-bold mb-2">📊 Confidence Score</h2>
          <p className="text-gray-400">Get probability-based results with each prediction.</p>
        </div>

      </div>

    </section>
  );
}