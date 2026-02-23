import { create } from 'zustand'

const useIncidentStore = create((set) => ({
  liveIncidents: [],        // real-time from WebSocket
  selectedIncident: null,
  wsConnected: false,

  addLiveIncident: (incident) =>
    set((state) => ({
      liveIncidents: [incident, ...state.liveIncidents].slice(0, 50) // keep last 50
    })),

  setSelected: (incident) => set({ selectedIncident: incident }),
  setWsConnected: (connected) => set({ wsConnected: connected }),
  clearLive: () => set({ liveIncidents: [] }),
}))

export default useIncidentStore
