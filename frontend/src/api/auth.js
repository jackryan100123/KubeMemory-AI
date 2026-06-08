/**
 * JWT authentication API (login / refresh).
 */
import axios from 'axios'
import client from './client'

const apiBase =
  import.meta.env.VITE_API_URL ||
  (import.meta.env.DEV ? 'http://localhost:8000/api' : null) ||
  (typeof window !== 'undefined' ? `${window.location.origin}/api` : 'http://localhost:8000/api')

/**
 * Obtain access and refresh tokens.
 * @param {{ username: string, password: string }} credentials
 */
export async function login(credentials) {
  const { data } = await axios.post(`${apiBase}/token/`, credentials, {
    headers: { 'Content-Type': 'application/json' },
    timeout: 30000,
  })
  return data
}

/**
 * Refresh access token.
 * @param {string} refreshToken
 */
export async function refreshToken(refreshToken) {
  const { data } = await client.post('/token/refresh/', { refresh: refreshToken })
  return data
}
