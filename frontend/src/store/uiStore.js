import { create } from 'zustand'
import { persist } from 'zustand/middleware'

/**
 * Client-only UI/settings state (theme, preferences).
 * Persisted to localStorage for Settings page.
 */
const useUiStore = create(
  persist(
    (set) => ({
      compactMode: false,
      refreshIntervalSeconds: 30,
      setCompactMode: (value) => set({ compactMode: value }),
      setRefreshIntervalSeconds: (value) =>
        set({ refreshIntervalSeconds: Math.max(10, Math.min(300, value)) }),
    }),
    { name: 'kubememory-ui' }
  )
)

export default useUiStore
