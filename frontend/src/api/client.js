import axios from 'axios'

// When built in Docker, .env is not available — use same origin so nginx can proxy /api to backend
const apiBase =
  import.meta.env.VITE_API_URL ||
  (typeof window !== 'undefined' ? `${window.location.origin}/api` : '/api')

const client = axios.create({
  baseURL: apiBase,
  headers: { 'Content-Type': 'application/json' },
  timeout: 30000,
})

// Request interceptor — add auth token when implemented
client.interceptors.request.use((config) => config)

// Response interceptor — global error handling; always log a clear message (never "undefined")
client.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status
    const data = error.response?.data
    const msg =
      (typeof data === 'object' && data !== null && (data.detail || data.error || data.message))
        ? String(data.detail || data.error || data.message)
        : typeof data === 'string'
          ? data
          : error.message || `Request failed${status ? ` (${status})` : ''}`
    console.error('API Error:', msg, status ? `[${status}]` : '')
    return Promise.reject(error)
  }
)

export default client
