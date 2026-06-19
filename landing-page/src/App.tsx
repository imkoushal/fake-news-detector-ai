import { Routes, Route, Navigate } from "react-router-dom"
import { Navbar } from "./components/Navbar"
import { HeroSection } from "./components/HeroSection"
import { HowItWorksSection } from "./components/HowItWorksSection"
import { AccuracySection } from "./components/AccuracySection"
import { Footer } from "./components/Footer"
import { AuthModal } from "./components/auth/AuthModal"
import { Dashboard } from "./pages/Dashboard"
import { AboutPage } from "./pages/About"
import { BatchPage } from "./pages/Batch"
import { AnalyticsPage } from "./pages/Analytics"
import { HistoryPage } from "./pages/History"
import { SettingsPage } from "./pages/Settings"
import { useAuth } from "./context/AuthContext"

function LandingPage() {
  const { user, isLoading } = useAuth();
  if (!isLoading && user) return <Navigate to="/dashboard" replace />;

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
          <Route path="/about" element={<AboutPage />} />
          <Route path="/batch" element={<BatchPage />} />
          <Route path="/analytics" element={<AnalyticsPage />} />
          <Route path="/history" element={<HistoryPage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Routes>
      </main>
    </div>
  )
}

export default App
