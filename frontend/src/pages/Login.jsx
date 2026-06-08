import { useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import toast from 'react-hot-toast'
import { login } from '../api/auth'
import useUiStore from '../store/uiStore'

/**
 * Login page — obtains JWT and stores tokens in memory (Zustand, not localStorage).
 */
export default function Login() {
  const navigate = useNavigate()
  const location = useLocation()
  const setAuth = useUiStore((s) => s.setAuth)
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)

  const from = location.state?.from?.pathname || '/'

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    try {
      const data = await login({ username, password })
      setAuth({
        accessToken: data.access,
        refreshToken: data.refresh,
        username,
      })
      toast.success('Signed in')
      navigate(from, { replace: true })
    } catch (err) {
      const msg =
        err.response?.data?.detail ||
        err.response?.data?.non_field_errors?.[0] ||
        'Login failed'
      toast.error(String(msg))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-bg flex items-center justify-center p-4">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-md bg-surface border border-surface2 rounded-lg p-8 shadow-lg"
      >
        <h1 className="text-2xl font-bold text-white mb-2">KubeMemory</h1>
        <p className="text-muted text-sm mb-6">Sign in to access the cluster brain</p>
        <p className="text-muted text-xs mb-6">
          Dev credentials come from <code className="text-accent">DEV_ADMIN_USERNAME</code> /{' '}
          <code className="text-accent">DEV_ADMIN_PASSWORD</code> in your <code>.env</code>. After
          changing them, run <code className="text-accent">ensure_dev_admin</code> in the API container.
        </p>
        <label className="block text-xs font-mono text-muted mb-1">Username</label>
        <input
          type="text"
          autoComplete="username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          className="w-full mb-4 px-3 py-2 rounded bg-bg border border-surface2 text-white"
          required
        />
        <label className="block text-xs font-mono text-muted mb-1">Password</label>
        <input
          type="password"
          autoComplete="current-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="w-full mb-6 px-3 py-2 rounded bg-bg border border-surface2 text-white"
          required
        />
        <button
          type="submit"
          disabled={loading}
          className="w-full py-2 rounded bg-accent text-bg font-semibold disabled:opacity-50"
        >
          {loading ? 'Signing in…' : 'Sign in'}
        </button>
      </form>
    </div>
  )
}
