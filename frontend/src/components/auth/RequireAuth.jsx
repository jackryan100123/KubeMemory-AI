import { Navigate, useLocation } from 'react-router-dom'
import useUiStore from '../../store/uiStore'

/**
 * Redirect to /login when no JWT is present in memory.
 */
export default function RequireAuth({ children }) {
  const accessToken = useUiStore((s) => s.accessToken)
  const envToken = import.meta.env.VITE_API_TOKEN
  const location = useLocation()

  if (accessToken || (envToken && String(envToken).trim())) {
    return children
  }

  return <Navigate to="/login" state={{ from: location }} replace />
}
