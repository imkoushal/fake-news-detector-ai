import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import { ToastProvider } from './context/ToastContext'
import './index.css'
import App from './App.tsx'

// Auto-detect system theme if no user preference saved
const savedTheme = localStorage.getItem('verifai_theme')
if (savedTheme) {
  document.documentElement.setAttribute('data-theme', savedTheme)
} else if (window.matchMedia?.('(prefers-color-scheme: light)').matches) {
  document.documentElement.setAttribute('data-theme', 'light')
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <ToastProvider>
          <App />
        </ToastProvider>
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>,
)

