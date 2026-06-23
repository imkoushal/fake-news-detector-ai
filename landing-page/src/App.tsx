import { Routes, Route, Navigate, Outlet } from "react-router-dom"
import { useState } from "react"
import { Navbar } from "./components/Navbar"
import { HeroSection } from "./components/HeroSection"
import { HowItWorksSection } from "./components/HowItWorksSection"
import { AccuracySection } from "./components/AccuracySection"
import { Footer } from "./components/Footer"
import { AppSidebar } from "./components/AppSidebar"
import { TopBar } from "./components/TopBar"
import { ScrollToTop } from "./components/ScrollToTop"
import { TopLoadingBar } from "./components/TopLoadingBar"
import { ShortcutsModal } from "./components/ShortcutsModal"
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

/* ─── Public landing page ─── */
function LandingPage() {
  const { user, isLoading } = useAuth()
  if (!isLoading && user) return <Navigate to="/dashboard" replace />
  return (
    <>
      <HeroSection />
      <HowItWorksSection />
      <AccuracySection />
      <Footer />
    </>
  )
}

/* ─── Public layout: floating navbar, no sidebar ─── */
function PublicLayout() {
  return (
    <div className="bg-hero-bg min-h-screen flex flex-col">
      <Navbar />
      <AuthModal />
      <main className="flex-1">
        <Outlet />
      </main>
    </div>
  )
}

/* ─── Auth layout: sidebar + topbar ─── */
function AuthLayout() {
  const { user } = useAuth()
  const [collapsed, setCollapsed] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)

  if (!user) return <Navigate to="/" replace />

  const sidebarWidth = collapsed ? 68 : 240

  return (
    <div className="min-h-screen bg-background flex">
      {/* Mobile overlay */}
      {mobileOpen && (
        <div className="fixed inset-0 bg-black/50 z-30 md:hidden" onClick={() => setMobileOpen(false)} />
      )}

      {/* Sidebar — desktop: fixed, mobile: slide-out */}
      <div className={`hidden md:block`}>
        <AppSidebar collapsed={collapsed} onToggle={() => setCollapsed(!collapsed)} />
      </div>
      <div className={`fixed inset-y-0 left-0 z-40 md:hidden transform transition-transform duration-300 ${mobileOpen ? "translate-x-0" : "-translate-x-full"}`}>
        <AppSidebar collapsed={false} onToggle={() => setMobileOpen(false)} />
      </div>

      {/* Main content area — no margin on mobile since sidebar is a drawer */}
      <div className="flex-1 flex flex-col min-h-screen transition-all duration-300 md:ml-[var(--sidebar-w)]" style={{ "--sidebar-w": `${sidebarWidth}px` } as React.CSSProperties}>
        <TopBar onMobileMenuToggle={() => setMobileOpen(!mobileOpen)} />
        <main id="main-content" className="flex-1 overflow-y-auto">
          <Outlet />
        </main>
      </div>
    </div>
  )
}

/* ─── Root App ─── */
function App() {
  return (
    <>
      <a href="#main-content" className="skip-to-content">Skip to content</a>
      <TopLoadingBar />
      <ShortcutsModal />
      <ScrollToTop />

      <Routes>
        {/* Public routes */}
        <Route element={<PublicLayout />}>
          <Route path="/" element={<LandingPage />} />
          <Route path="/about" element={<AboutPage />} />
        </Route>

        {/* Authenticated routes — sidebar layout */}
        <Route element={<AuthLayout />}>
          <Route path="/dashboard" element={<Dashboard />} />
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
