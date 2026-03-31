import { motion } from "framer-motion";

export default function Footer() {
  const currentYear = new Date().getFullYear();

  return (
    <motion.footer
      initial={{ opacity: 0 }}
      whileInView={{ opacity: 1 }}
      viewport={{ once: true }}
      transition={{ duration: 0.6 }}
      className="relative border-t border-white/[0.06]"
    >
      {/* Subtle top glow line */}
      <div
        className="absolute top-0 left-1/2 -translate-x-1/2 w-1/3 h-px bg-gradient-to-r from-transparent via-purple-500/40 to-transparent"
        aria-hidden="true"
      />

      <div className="max-w-6xl mx-auto px-6 py-10">
        <div className="flex flex-col md:flex-row items-center justify-between gap-6">
          {/* Left — branding */}
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-purple-500 to-blue-500 flex items-center justify-center">
              <svg
                className="w-3.5 h-3.5 text-white"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2.5}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M9.75 3.104v5.714a2.25 2.25 0 0 1-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 0 1 4.5 0m0 0v5.714a2.25 2.25 0 0 0 .659 1.591L19 14.5"
                />
              </svg>
            </div>
            <span className="text-sm font-semibold text-slate-300 tracking-tight">
              FakeNews AI
            </span>
          </div>

          {/* Center — copyright */}
          <p className="text-sm text-slate-500 text-center order-last md:order-none">
            © {currentYear} FakeNews AI. Built with FastAPI & React.
          </p>

          {/* Right — tech stack pills */}
          <div className="flex items-center gap-2">
            {["FastAPI", "React", "SVM"].map((tech) => (
              <span
                key={tech}
                className="px-2.5 py-1 rounded-full text-[10px] font-medium tracking-wide text-slate-500 bg-white/[0.04] border border-white/[0.06]"
              >
                {tech}
              </span>
            ))}
          </div>
        </div>
      </div>
    </motion.footer>
  );
}
