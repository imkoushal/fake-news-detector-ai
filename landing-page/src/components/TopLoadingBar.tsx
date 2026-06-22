import { useEffect, useState } from "react"
import { useLocation } from "react-router-dom"

export function TopLoadingBar() {
  const [progress, setProgress] = useState(0)
  const [visible, setVisible] = useState(false)
  const location = useLocation()

  useEffect(() => {
    // Reset on route change
    setProgress(30)
    setVisible(true)
    const t1 = setTimeout(() => setProgress(60), 100)
    const t2 = setTimeout(() => setProgress(100), 300)
    const t3 = setTimeout(() => setVisible(false), 500)
    return () => { clearTimeout(t1); clearTimeout(t2); clearTimeout(t3) }
  }, [location.pathname])

  if (!visible) return null

  return (
    <div className="fixed top-0 left-0 right-0 z-[100] h-[2px]">
      <div className="h-full bg-primary transition-all duration-300 ease-out" style={{ width: `${progress}%` }} />
    </div>
  )
}
