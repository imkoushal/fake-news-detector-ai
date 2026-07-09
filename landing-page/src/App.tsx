import { Routes, Route, Navigate, Outlet } from "react-router-dom"
import { useState, lazy, Suspense } from "react"
import { Navbar } from "./components/Navbar"
import { AppSidebar } from "./components/AppSidebar"
import { TopBar } from "./components/TopBar"
import { ScrollToTop } from "./components/ScrollToTop"
import { TopLoadingBar } from "./components/TopLoadingBar"
import { ShortcutsModal } from "./components/ShortcutsModal"
import { AuthModal } from "./components/auth/AuthModal"
import { useAuth } from "./context/AuthContext"

/* ─── Lazy-loaded page components (code-splitting) ─── */
const HeroSection = lazy(() => import("./components/HeroSection").then(m => ({ default: m.HeroSection })))
const HowItWorksSection = lazy(() => import("./components/HowItWorksSection").then(m => ({ default: m.HowItWorksSection })))
const AccuracySection = lazy(() => import("./components/AccuracySection").then(m => ({ default: m.AccuracySection })))
const Footer = lazy(() => import("./components/Footer").then(m => ({ default: m.Footer })))
const Dashboard = lazy(() => import("./pages/Dashboard").then(m => ({ default: m.Dashboard })))
const AboutPage = lazy(() => import("./pages/About").then(m => ({ default: m.AboutPage })))
const BatchPage = lazy(() => import("./pages/Batch").then(m => ({ default: m.BatchPage })))
const AnalyticsPage = lazy(() => import("./pages/Analytics").then(m => ({ default: m.AnalyticsPage })))
const HistoryPage = lazy(() => import("./pages/History").then(m => ({ default: m.HistoryPage })))
const SettingsPage = lazy(() => import("./pages/Settings").then(m => ({ default: m.SettingsPage })))
const ComparePage = lazy(() => import("./pages/Compare").then(m => ({ default: m.ComparePage })))
const BookmarksPage = lazy(() => import("./pages/Bookmarks").then(m => ({ default: m.BookmarksPage })))
const FeedbackPage = lazy(() => import("./pages/Feedback").then(m => ({ default: m.FeedbackPage })))
const ClaimPage = lazy(() => import("./pages/Claim").then(m => ({ default: m.Claim })))

/* ─── Skeleton fallback for lazy-loaded routes ─── */
function PageSkeleton() {
  return (
    <div className="p-6 md:p-8 animate-fade-in">
      <div className="max-w-6xl mx-auto space-y-6">
        <div className="skeleton h-8 w-48" />
        <div className="skeleton h-4 w-72" />
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mt-6">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="skeleton h-24 rounded-2xl" />
          ))}
        </div>
        <div className="skeleton h-64 rounded-2xl mt-4" />
      </div>
    </div>
  )
}

/* ─── Public landing page ─── */
function LandingPage() {
  const { user, isLoading } = useAuth()
  if (!isLoading && user) return <Navigate to="/dashboard" replace />
  return (
    <Suspense fallback={<PageSkeleton />}>
      <HeroSection />
      <HowItWorksSection />
      <AccuracySection />
      <Footer />
    </Suspense>
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
  const { user, isLoading } = useAuth()
  const [collapsed, setCollapsed] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)

  // Wait for auth check to complete before deciding to redirect
  if (isLoading) return <div className="min-h-screen bg-background flex items-center justify-center"><PageSkeleton /></div>
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
          <Suspense fallback={<PageSkeleton />}>
            <Outlet />
          </Suspense>
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
        {/* Standalone routes */}
        <Route path="/claim/:hash" element={<Suspense fallback={<PageSkeleton />}><ClaimPage /></Suspense>} />

        {/* Public routes */}
        <Route element={<PublicLayout />}>
          <Route path="/" element={<LandingPage />} />
          <Route path="/about" element={<Suspense fallback={<PageSkeleton />}><AboutPage /></Suspense>} />
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
