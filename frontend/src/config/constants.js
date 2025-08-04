// Global configuration constants
export const APP_CONFIG = {
  // Domain configuration
  DOMAIN: import.meta.env.VITE_APP_DOMAIN || 'http://localhost:5173',
  API_BASE_URL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  
  // App settings
  MAX_PLAYLIST_SIZE: 30,
  MAX_REFINEMENTS: 10
}