import { motion } from "framer-motion";

export default function Hero() {
  return (
    <section id="home" className="min-h-screen flex items-center justify-center px-6 pt-20">

      {/* Glow background */}
      <div className="absolute w-[500px] h-[500px] bg-purple-500 opacity-30 blur-3xl rounded-full top-[-100px] left-[-100px]"></div>
      <div className="absolute w-[400px] h-[400px] bg-blue-500 opacity-30 blur-3xl rounded-full bottom-[-100px] right-[-100px]"></div>

      {/* Main card */}
      <motion.div
        initial={{ opacity: 0, y: 40 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8 }}
        className="bg-white/10 backdrop-blur-xl border border-white/20 rounded-3xl p-10 text-center shadow-2xl max-w-2xl"
      >
        <h1 className="text-5xl font-bold mb-4">
          Detect Fake News Instantly
        </h1>

        <p className="text-gray-300 mb-6">
          AI-powered system to verify news authenticity in seconds.
        </p>

        <a
          href="#analyze"
          className="px-6 py-3 bg-gradient-to-r from-purple-500 to-blue-500 rounded-full hover:scale-105 transition"
        >
          Try Now
        </a>
      </motion.div>
    </section>
  );
}