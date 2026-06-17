import { Routes, Route } from "react-router-dom"
import { Navbar } from "./components/Navbar"
import { HeroSection } from "./components/HeroSection"
import { HowItWorksSection } from "./components/HowItWorksSection"
import { AccuracySection } from "./components/AccuracySection"
import { Footer } from "./components/Footer"
import { AuthModal } from "./components/auth/AuthModal"
import { Dashboard } from "./pages/Dashboard"

function LandingPage() {
  return (
    <>
      <HeroSection />
      <HowItWorksSection />
      <AccuracySection />
      <Footer />
    </>
  )
}

function App() {
  return (
    <div className="bg-hero-bg min-h-screen flex flex-col">
      <Navbar />
      <AuthModal />
      
      <main className="flex-1">
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/dashboard" element={<Dashboard />} />
        </Routes>
      </main>
    </div>
  )
}

export default App
