import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig(({ command }) => ({
  plugins: [react(), tailwindcss()],
  // GitHub Pages project site. Development stays at the server root.
  base: command === 'build' ? '/online-Safety-Global-Tracker-/' : '/',
}))
