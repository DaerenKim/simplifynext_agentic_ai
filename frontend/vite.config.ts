import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __filename = fileURLToPath(import.meta.url)
const __dirname  = path.dirname(__filename)

export default defineConfig({
  server: {
    host: 'localhost',
    port: 5173,
    proxy: {
      // OAuth endpoints - HTTPS with self-signed cert handling
      '/oauth2': {
        target: 'https://localhost:8080',
        changeOrigin: true,
        secure: false,
        configure: (proxy, _options) => {
          proxy.on('error', (err, _req, _res) => {
            console.log('OAuth proxy error:', err);
          });
        },
      },
      
      // ALL API endpoints go to the unified Flask server on 8081
      '/api/manager': {
        target: 'http://localhost:8081',
        changeOrigin: true,
      },
      '/api/secretary': {
        target: 'http://localhost:8081',
        changeOrigin: true,
      },
      '/api/secretary-tools': {
        target: 'http://localhost:8081',
        changeOrigin: true,
      },
      '/api/scheduler': {
        target: 'http://localhost:8081',
        changeOrigin: true,
      },
      '/api/scheduler-tools': {
        target: 'http://localhost:8081',
        changeOrigin: true,
      },
      '/api/therapist': {
        target: 'http://localhost:8081',
        changeOrigin: true,
      },
      
      // Calendar endpoints - HTTPS with self-signed cert handling
      '/api/calendar': {
        target: 'https://localhost:8080',
        changeOrigin: true,
        secure: false,
        configure: (proxy, _options) => {
          proxy.on('error', (err, _req, _res) => {
            console.log('Calendar proxy error:', err);
          });
          proxy.on('proxyReq', (proxyReq, req, _res) => {
            console.log('Proxying calendar request:', req.method, req.url);
          });
        },
      },
      
      // Debug endpoints
      '/debug': {
        target: 'http://localhost:8081',
        changeOrigin: true,
      },
      '/health': {
        target: 'http://localhost:8081',
        changeOrigin: true,
      },
    },
  },
  plugins: [react()],
  resolve: { alias: { '@': path.resolve(__dirname, './src') } },
})