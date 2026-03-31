import { motion } from "framer-motion";

const FEATURES = [
  {
    icon: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z" />
      </svg>
    ),
    title: "Fast Detection",
    description: "Analyze news instantly using optimized machine learning models with sub-second response times.",
    accent: "from-amber-400 to-orange-500",
    glow: "group-hover:shadow-amber-500/20",
  },
  {
    icon: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09ZM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456ZM16.894 20.567L16.5 21.75l-.394-1.183a2.25 2.25 0 00-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 001.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 001.423 1.423l1.183.394-1.183.394a2.25 2.25 0 00-1.423 1.423Z" />
      </svg>
    ),
    title: "AI Powered",
    description: "Built using NLP and advanced ML algorithms — SVM classifiers with TF-IDF feature extraction for high accuracy.",
    accent: "from-purple-400 to-violet-500",
    glow: "group-hover:shadow-purple-500/20",
  },
  {
    icon: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75ZM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625ZM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125Z" />
      </svg>
    ),
    title: "Confidence Score",
    description: "Get probability-based confidence for every prediction with visual progress indicators.",
    accent: "from-blue-400 to-cyan-500",
    glow: "group-hover:shadow-blue-500/20",
  },
  {
    icon: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 21a9.004 9.004 0 008.716-6.747M12 21a9.004 9.004 0 01-8.716-6.747M12 21c2.485 0 4.5-4.03 4.5-9S14.485 3 12 3m0 18c-2.485 0-4.5-4.03-4.5-9S9.515 3 12 3m0 0a8.997 8.997 0 017.843 4.582M12 3a8.997 8.997 0 00-7.843 4.582m15.686 0A11.953 11.953 0 0112 10.5c-2.998 0-5.74-1.1-7.843-2.918m15.686 0A8.959 8.959 0 0121 12c0 .778-.099 1.533-.284 2.253m0 0A17.919 17.919 0 0112 16.5c-3.162 0-6.133-.815-8.716-2.247m0 0A9.015 9.015 0 013 12c0-1.605.42-3.113 1.157-4.418" />
      </svg>
    ),
    title: "Multilingual Ready",
    description: "Supports multiple languages with automatic translation capabilities — expanding soon.",
    accent: "from-emerald-400 to-teal-500",
    glow: "group-hover:shadow-emerald-500/20",
    badge: "Coming Soon",
  },
  {
    icon: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
    title: "History Tracking",
    description: "Keep track of every analyzed article with timestamps, stored locally on your device.",
    accent: "from-pink-400 to-rose-500",
    glow: "group-hover:shadow-pink-500/20",
  },
  {
    icon: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285Z" />
      </svg>
    ),
    title: "Reliable & Secure",
    description: "Your data is processed securely with no storage of sensitive inputs on our servers.",
    accent: "from-slate-300 to-slate-400",
    glow: "group-hover:shadow-slate-400/15",
  },
];

const containerVariants = {
  hidden: {},
  visible: {
    transition: { staggerChildren: 0.1, delayChildren: 0.2 },
  },
};

const cardVariants = {
  hidden: { opacity: 0, y: 35 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.55, ease: [0.25, 0.46, 0.45, 0.94] },
  },
};

export default function Features() {
  return (
    <section
      id="features"
      className="min-h-screen flex flex-col items-center justify-center px-6 py-24"
    >
      {/* ── Section heading ── */}
      <motion.div
        initial={{ opacity: 0, y: 25 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, margin: "-80px" }}
        transition={{ duration: 0.6, ease: [0.25, 0.46, 0.45, 0.94] }}
        className="text-center mb-14"
      >
        <span className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full text-xs font-medium tracking-wide bg-blue-500/10 text-blue-300 border border-blue-500/20 mb-5">
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09Z" />
          </svg>
          What We Offer
        </span>

        <h2 className="text-3xl md:text-4xl font-bold bg-gradient-to-r from-purple-400 via-violet-400 to-blue-400 bg-clip-text text-transparent">
          Powerful Features
        </h2>
        <p className="text-slate-400 text-sm md:text-base mt-3 max-w-lg mx-auto leading-relaxed">
          Designed to help you detect fake news quickly and accurately with state-of-the-art AI tools.
        </p>
      </motion.div>

      {/* ── Feature grid ── */}
      <motion.div
        variants={containerVariants}
        initial="hidden"
        whileInView="visible"
        viewport={{ once: true, margin: "-60px" }}
        className="grid md:grid-cols-2 lg:grid-cols-3 gap-5 max-w-6xl mx-auto w-full"
      >
        {FEATURES.map((feature) => (
          <motion.div
            key={feature.title}
            variants={cardVariants}
            className={`group relative bg-white/[0.03] backdrop-blur-2xl border border-white/[0.07] rounded-2xl p-7
                       hover:bg-white/[0.07] hover:border-white/[0.15]
                       hover:scale-[1.03] hover:-translate-y-1
                       shadow-lg shadow-transparent ${feature.glow} hover:shadow-xl
                       transition-all duration-300 ease-out cursor-default`}
          >
            {/* Badge */}
            {feature.badge && (
              <span className="absolute top-4 right-4 px-2.5 py-0.5 rounded-full text-[10px] font-semibold tracking-wide uppercase bg-violet-500/15 text-violet-300 border border-violet-500/25">
                {feature.badge}
              </span>
            )}

            {/* Icon circle */}
            <div
              className={`w-11 h-11 rounded-xl bg-gradient-to-br ${feature.accent} flex items-center justify-center mb-5 text-white
                          shadow-lg shadow-transparent group-hover:shadow-current/20
                          group-hover:scale-110 transition-all duration-300`}
            >
              {feature.icon}
            </div>

            {/* Title */}
            <h3 className="text-lg font-semibold text-white mb-2 tracking-tight">
              {feature.title}
            </h3>

            {/* Description */}
            <p className="text-sm text-slate-400 leading-relaxed">
              {feature.description}
            </p>
          </motion.div>
        ))}
      </motion.div>
    </section>
  );
}