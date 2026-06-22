import { Routes, Route, Navigate } from "react-router-dom"
import { HeroSection } from "./components/HeroSection"
import { HowItWorksSection } from "./components/HowItWorksSection"
import { AccuracySection } from "./components/AccuracySection"
import { Footer } from "./components/Footer"
import { ScrollToTop } from "./components/ScrollToTop"
import { TopLoadingBar } from "./components/TopLoadingBar"
import { ShortcutsModal } from "./components/ShortcutsModal"
import { AuthLayout } from "./layouts/AuthLayout"
import { PublicLayout } from "./layouts/PublicLayout"
import { AuthModal } from "./components/auth/AuthModal"
import { Dashboard } from "./pages/Dashboard"
import { AboutPage } from "./pages/About"
import { BatchPage } from "./pages/Batch"
import { AnalyticsPage } from "./pages/Analytics"
import { HistoryPage } from "./pages/History"
import { SettingsPage } from "./pages/Settings"
import { ComparePage } from "./pages/Compare"
import { BookmarksPage } from "./pages/Bookmarks"
import { FeedbackPage } from "./pages/Feedback"
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
    <>
      <a href="#main-content" className="skip-to-content">Skip to content</a>
      <TopLoadingBar />
      <AuthModal />
      <ShortcutsModal />
      <ScrollToTop />
      
      <Routes>
        {/* Public Routes */}
        <Route element={<PublicLayout />}>
          <Route path="/" element={<LandingPage />} />
        </Route>

        {/* Authenticated Routes */}
        <Route element={<AuthLayout />}>
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/about" element={<AboutPage />} />
          <Route path="/batch" element={<BatchPage />} />
          <Route path="/analytics" element={<AnalyticsPage />} />
          <Route path="/history" element={<HistoryPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/compare" element={<ComparePage />} />
          <Route path="/bookmarks" element={<BookmarksPage />} />
          <Route path="/feedback" element={<FeedbackPage />} />
        </Route>
      </Routes>
    </>
  )
}

export default App
