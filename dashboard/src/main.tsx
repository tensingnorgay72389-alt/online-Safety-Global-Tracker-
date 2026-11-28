import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'

// Older links used a hash route. Keep them working after the move to path routes.
const hashRoute = window.location.hash
if (hashRoute.startsWith('#/')) {
  const base = import.meta.env.BASE_URL.replace(/\/$/, '')
  window.history.replaceState(null, '', `${base}${hashRoute.slice(1)}${window.location.search}`)
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
