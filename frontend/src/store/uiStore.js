import { create } from 'zustand'
import { persist } from 'zustand/middleware'

/**
 * UI settings (persisted) and JWT tokens (memory only — never localStorage).
 */
const useUiStore = create(
  persist(
    (set, get) => ({
      compactMode: false,
      refreshIntervalSeconds: 30,
      accessToken: null,
      refreshToken: null,
      username: null,
      setCompactMode: (value) => set({ compactMode: value }),
      setRefreshIntervalSeconds: (value) =>
        set({ refreshIntervalSeconds: Math.max(10, Math.min(300, value)) }),
      setAuth: ({ accessToken, refreshToken, username }) =>
        set({ accessToken, refreshToken, username }),
      clearAuth: () => set({ accessToken: null, refreshToken: null, username: null }),
      getAccessToken: () => get().accessToken,
    }),
    {
      name: 'kubememory-ui',
      partialize: (state) => ({
        compactMode: state.compactMode,
        refreshIntervalSeconds: state.refreshIntervalSeconds,
      }),
    }
  )
)

// Optional bootstrap token from env (automation only; not persisted)
const envToken = import.meta.env.VITE_API_TOKEN
if (envToken && typeof envToken === 'string' && envToken.trim()) {
  useUiStore.setState({ accessToken: envToken.trim() })
}

export default useUiStore
