import { Capacitor } from '@capacitor/core';

// Production backend URL (Render deployment)
const PRODUCTION_API = 'https://fake-news-detector-8djq.onrender.com';

// API Base URL config
// - DEV mode: local FastAPI server
// - Native (Capacitor WebView): hardcoded production URL
//   (window.location.origin returns "capacitor://localhost" inside WebView)
// - Web production: same-origin (served by the same Render deployment)
export const API_BASE = import.meta.env.DEV
  ? 'http://localhost:8000'
  : Capacitor.isNativePlatform()
    ? PRODUCTION_API
    : window.location.origin;

// Helper to get auth headers
export const getAuthHeaders = () => {
  const token = localStorage.getItem('verify_token');
  return {
    'Content-Type': 'application/json',
    ...(token ? { 'Authorization': `Bearer ${token}` } : {})
  };
};
