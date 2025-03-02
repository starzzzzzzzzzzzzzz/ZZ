import { defineStore } from 'pinia'

export const useAppStore = defineStore('app', {
  state: () => ({
    currentKnowledgeBase: null as number | null,
    loading: false,
    error: null as string | null
  }),
  
  actions: {
    setCurrentKnowledgeBase(id: number | null) {
      this.currentKnowledgeBase = id
    },
    setLoading(status: boolean) {
      this.loading = status
    },
    setError(error: string | null) {
      this.error = error
    }
  }
}) 