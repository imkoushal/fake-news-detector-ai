// API Base URL config
export const API_BASE = import.meta.env.DEV 
  ? 'http://localhost:8000' 
  : window.location.origin;

// Helper to get auth headers
export const getAuthHeaders = () => {
  const token = localStorage.getItem('verify_token');
  return {
    'Content-Type': 'application/json',
    ...(token ? { 'Authorization': `Bearer ${token}` } : {})
  };
};
