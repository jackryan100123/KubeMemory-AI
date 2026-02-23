import axios from 'axios'

const client = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
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
