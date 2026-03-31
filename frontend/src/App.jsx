import { useState, useEffect } from "react";
import Navbar from "./components/Navbar";
import Footer from "./components/Footer";
import Hero from "./sections/Hero";
import Analyze from "./sections/Analyze";
import Features from "./sections/Features";
import History from "./sections/History";

function App() {
  const [pos, setPos] = useState({ x: 0, y: 0 });

  useEffect(() => {
    const move = (e) => {
      setPos({ x: e.clientX, y: e.clientY });
    };

    window.addEventListener("mousemove", move);
    return () => window.removeEventListener("mousemove", move);
  }, []);

  return (
    <div className="relative">
      {/* Animated background blobs */}
      <div className="fixed inset-0 -z-10 overflow-hidden pointer-events-none" aria-hidden="true">
        <div className="absolute w-[500px] h-[500px] bg-purple-500/20 blur-3xl rounded-full top-[-100px] left-[-100px] animate-pulse" />
        <div className="absolute w-[400px] h-[400px] bg-blue-500/20 blur-3xl rounded-full bottom-[-100px] right-[-100px] animate-pulse" />
      </div>

      {/* Cursor glow */}
      <div
        className="fixed w-40 h-40 bg-purple-500/20 blur-2xl rounded-full pointer-events-none z-0 transition-transform duration-75 ease-out"
        style={{
          top: pos.y - 80,
          left: pos.x - 80,
        }}
        aria-hidden="true"
      />

      <Navbar />
      <Hero />
      <Analyze />
      <History />
      <Features />
      <Footer />
    </div>
  );
}

export default App;