import { useState } from "react"
import { Navigate, Outlet } from "react-router-dom"
import { useAuth } from "../context/AuthContext"
import { AppSidebar } from "../components/AppSidebar"
import { TopBar } from "../components/TopBar"
import { MobileNav } from "../components/MobileNav"

export function AuthLayout() {
  const { user, isLoading } = useAuth()
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  if (isLoading) return <div className="min-h-screen bg-background flex items-center justify-center text-foreground">Loading...</div>
  if (!user) return <Navigate to="/" replace />

  return (
    <div className="flex min-h-screen bg-background">
      <AppSidebar />
      <div className="flex-1 flex flex-col md:ml-64 min-w-0">
        <TopBar onMobileMenuClick={() => setMobileMenuOpen(true)} />
        <main className="flex-1 p-4 md:p-8 overflow-x-hidden">
          <Outlet />
        </main>
      </div>
      
      {/* Mobile navigation drawer (handled in MobileNav component) */}
      <MobileNav open={mobileMenuOpen} onClose={() => setMobileMenuOpen(false)} />
    </div>
  )
}
