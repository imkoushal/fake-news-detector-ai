import { useState, useEffect } from "react"

/**
 * Detects if the current viewport is mobile-sized (< 768px).
 * Uses `window.matchMedia` for efficient, debounced detection.
 * Responds to both resize and orientation change events.
 */
export function useIsMobile(breakpoint = 768): boolean {
  const [isMobile, setIsMobile] = useState(() => {
    if (typeof window === "undefined") return false
    return window.innerWidth < breakpoint
  })

  useEffect(() => {
    const mql = window.matchMedia(`(max-width: ${breakpoint - 1}px)`)
    const handler = (e: MediaQueryListEvent) => setIsMobile(e.matches)

    // Set initial state from the media query
    setIsMobile(mql.matches)

    mql.addEventListener("change", handler)
    return () => mql.removeEventListener("change", handler)
  }, [breakpoint])

  return isMobile
}
