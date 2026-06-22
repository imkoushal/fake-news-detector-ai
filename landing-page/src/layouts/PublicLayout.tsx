import { Outlet } from "react-router-dom"
import { Navbar } from "../components/Navbar"
import { AppFooter } from "../components/AppFooter"

export function PublicLayout() {
  return (
    <div className="bg-hero-bg min-h-screen flex flex-col">
      <Navbar />
      <main className="flex-1">
        <Outlet />
      </main>
      <AppFooter />
    </div>
  )
}
