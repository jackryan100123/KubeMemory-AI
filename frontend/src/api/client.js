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

// Response interceptor — global error handling
client.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error.response?.data)
    return Promise.reject(error)
  }
)

export default client
