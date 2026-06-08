import axios from 'axios'
import useUiStore from '../store/uiStore'

const apiBase =
  import.meta.env.VITE_API_URL ||
  (import.meta.env.DEV ? 'http://localhost:8000/api' : null) ||
  (typeof window !== 'undefined' ? `${window.location.origin}/api` : 'http://localhost:8000/api')

const client = axios.create({
  baseURL: apiBase,
  headers: { 'Content-Type': 'application/json' },
  timeout: 30000,
})

client.interceptors.request.use((config) => {
  const url = config.url || ''
  if (url.includes('/token/')) {
    return config
  }
  const token = useUiStore.getState().getAccessToken?.() || useUiStore.getState().accessToken
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

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
    if (status === 401 && typeof window !== 'undefined' && !window.location.pathname.startsWith('/login')) {
      useUiStore.getState().clearAuth()
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export default client
