import { motion } from "framer-motion";

const containerVariants = {
  hidden: {},
  visible: {
    transition: { staggerChildren: 0.13, delayChildren: 0.2 },
  },
};

const fadeUp = {
  hidden: { opacity: 0, y: 40 },
  visible: (delay = 0) => ({
    opacity: 1,
    y: 0,
    transition: { duration: 0.7, ease: [0.25, 0.46, 0.45, 0.94], delay },
  }),
};

export default function Hero() {
  return (
    <section
      id="home"
      className="relative min-h-screen flex items-center justify-center px-6 pt-20 overflow-hidden"
    >
      {/* ── Animated glow blobs ── */}
      <div className="pointer-events-none absolute inset-0 overflow-hidden" aria-hidden="true">
        {/* Purple glow — top-left */}
        <div
          className="absolute -top-40 -left-40 w-[650px] h-[650px] rounded-full opacity-30"
          style={{
            background:
              "radial-gradient(circle, rgba(147,51,234,0.55) 0%, rgba(124,58,237,0.20) 45%, transparent 70%)",
            animation: "float-slow 14s ease-in-out infinite, pulse-glow 6s ease-in-out infinite",
          }}
        />
        {/* Blue glow — bottom-right */}
        <div
          className="absolute -bottom-44 -right-44 w-[550px] h-[550px] rounded-full opacity-25"
          style={{
            background:
              "radial-gradient(circle, rgba(59,130,246,0.50) 0%, rgba(37,99,235,0.18) 45%, transparent 70%)",
            animation:
              "float-slow 16s ease-in-out infinite reverse, pulse-glow 7s ease-in-out infinite 2s",
          }}
        />
        {/* Cyan accent — center */}
        <div
          className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[350px] h-[350px] rounded-full opacity-15"
          style={{
            background:
              "radial-gradient(circle, rgba(6,182,212,0.40) 0%, transparent 65%)",
            animation: "float-slow 12s ease-in-out infinite 3s",
          }}
        />
      </div>

      {/* ── Glassmorphism card ── */}
      <motion.div
        initial="hidden"
        whileInView="visible"
        viewport={{ once: true }}
        variants={containerVariants}
        className="relative z-10 w-full max-w-2xl"
      >
        <div
          className="bg-white/[0.04] backdrop-blur-2xl rounded-3xl p-10 md:p-14 text-center
                     border border-white/[0.08]
                     shadow-[0_8px_80px_-20px_rgba(139,92,246,0.22),0_0_0_1px_rgba(255,255,255,0.03)]"
        >
          {/* Badge */}
          <motion.div variants={fadeUp} custom={0}>
            <span
              className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full text-xs font-medium tracking-wide
                         bg-gradient-to-r from-purple-500/10 to-blue-500/10
                         text-purple-300 border border-purple-500/20 mb-8"
            >
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-purple-400 opacity-75" />
                <span className="relative inline-flex rounded-full h-2 w-2 bg-purple-400" />
              </span>
              Powered by Machine Learning
            </span>
          </motion.div>

          {/* Heading */}
          <motion.h1
            variants={fadeUp}
            custom={0.1}
            className="text-4xl sm:text-5xl md:text-6xl font-extrabold leading-[1.1] tracking-tight"
          >
            <span className="bg-gradient-to-br from-white via-slate-200 to-slate-400 bg-clip-text text-transparent">
              AI-Powered
            </span>
            <br />
            <span className="bg-gradient-to-r from-purple-400 via-violet-400 to-blue-400 bg-clip-text text-transparent">
              Fake News Detection
            </span>
          </motion.h1>

          {/* Subtext */}
          <motion.p
            variants={fadeUp}
            custom={0.2}
            className="text-base md:text-lg text-slate-400 mt-5 max-w-md mx-auto leading-relaxed"
          >
            Analyze and verify news instantly using machine learning.
            <br className="hidden sm:block" />
            Know the truth before you share.
          </motion.p>

          {/* CTA Buttons */}
          <motion.div
            variants={fadeUp}
            custom={0.3}
            className="mt-9 flex flex-col sm:flex-row items-center justify-center gap-4"
          >
            <a
              href="#analyze"
              id="hero-cta-analyze"
              className="group relative inline-flex items-center gap-2 px-8 py-3.5 rounded-full font-semibold text-white
                         bg-gradient-to-r from-purple-600 via-violet-600 to-blue-600
                         shadow-lg shadow-purple-600/25
                         hover:shadow-[0_0_30px_rgba(139,92,246,0.4)] hover:scale-105
                         hover:from-purple-500 hover:via-violet-500 hover:to-blue-500
                         active:scale-[0.97]
                         transition-all duration-300 ease-out"
            >
              {/* Shimmer overlay */}
              <span
                className="absolute inset-0 rounded-full overflow-hidden"
                aria-hidden="true"
              >
                <span className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-700 ease-in-out" />
              </span>
              <span className="relative">Analyze Now</span>
              <svg
                className="relative w-4 h-4 transition-transform duration-300 group-hover:translate-x-1"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2.5}
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M13 7l5 5m0 0l-5 5m5-5H6" />
              </svg>
            </a>

            <a
              href="#features"
              id="hero-cta-features"
              className="inline-flex items-center gap-2 px-6 py-3.5 rounded-full font-medium text-slate-300
                         border border-white/10 hover:border-white/25
                         hover:bg-white/[0.06] hover:scale-105
                         hover:shadow-lg hover:shadow-white/[0.03]
                         active:scale-[0.97]
                         transition-all duration-300 ease-out"
            >
              Learn More
            </a>
          </motion.div>

          {/* Stats row */}
          <motion.div
            variants={fadeUp}
            custom={0.45}
            className="mt-10 pt-8 border-t border-white/[0.06] flex items-center justify-center gap-8 md:gap-14"
          >
            {[
              { value: "95%+", label: "Accuracy" },
              { value: "<1s", label: "Response" },
              { value: "Free", label: "To Use" },
            ].map((stat) => (
              <div key={stat.label} className="text-center">
                <p className="text-xl md:text-2xl font-bold bg-gradient-to-r from-purple-300 to-blue-300 bg-clip-text text-transparent">
                  {stat.value}
                </p>
                <p className="text-[11px] text-slate-500 mt-1 tracking-widest uppercase font-medium">
                  {stat.label}
                </p>
              </div>
            ))}
          </motion.div>
        </div>
      </motion.div>
    </section>
  );
}