/**
 * Cattle Store - Manages cattle data and related operations
 */

import { defineStore } from 'pinia'
import { useAPIService } from '@/services/apiService'

export const useCattleStore = defineStore('cattle', {
  state: () => ({
    cattleList: [],
    selectedCattle: null,
    loading: false,
    error: null,
    lastUpdated: null
  }),

  getters: {
    // Get cattle by ID
    getCattleById: (state) => (id) => {
      return state.cattleList.find(cattle => cattle.id === id)
    },

    // Get cattle by identifier
    getCattleByIdentifier: (state) => (identifier) => {
      return state.cattleList.find(cattle => cattle.identifier === identifier)
    },

    // Get healthy cattle
    healthyCattle: (state) => {
      return state.cattleList.filter(cattle => cattle.healthStatus === 'Sehat')
    },

    // Get cattle needing attention
    cattleNeedingAttention: (state) => {
      return state.cattleList.filter(cattle => cattle.healthStatus === 'Perlu Perhatian')
    },

    // Get sick cattle
    sickCattle: (state) => {
      return state.cattleList.filter(cattle => cattle.healthStatus === 'Sakit')
    },

    // Get cattle outside geofence
    cattleOutsideGeofence: (state) => {
      return state.cattleList.filter(cattle => cattle.geofenceStatus === 'outside')
    },

    // Get total count
    totalCount: (state) => state.cattleList.length,

    // Get statistics
    statistics: (state) => {
      return {
        total: state.cattleList.length,
        healthy: state.cattleList.filter(c => c.healthStatus === 'Sehat').length,
        needingAttention: state.cattleList.filter(c => c.healthStatus === 'Perlu Perhatian').length,
        sick: state.cattleList.filter(c => c.healthStatus === 'Sakit').length,
        outsideGeofence: state.cattleList.filter(c => c.geofenceStatus === 'outside').length,
        averageAge: state.cattleList.reduce((sum, c) => sum + c.age, 0) / state.cattleList.length || 0
      }
    }
  },

  actions: {
    // API Service
    apiService: useAPIService(),

    // Fetch all cattle
    async fetchCattle() {
      this.loading = true
      this.error = null

      try {
        const response = await this.apiService.getCattle()
        this.cattleList = this.apiService.transformCattleData(response)
        this.lastUpdated = new Date()
      } catch (error) {
        this.error = error.message
        console.error('Failed to fetch cattle:', error)
        throw error
      } finally {
        this.loading = false
      }
    },

    // Fetch cattle by ID
    async fetchCattleById(cattleId) {
      this.loading = true
      this.error = null

      try {
        const response = await this.apiService.getCattleById(cattleId)
        const cattle = this.apiService.transformCattleData([response])[0]

        // Update or add to list
        const existingIndex = this.cattleList.findIndex(c => c.id === cattleId)
        if (existingIndex >= 0) {
          this.cattleList[existingIndex] = cattle
        } else {
          this.cattleList.push(cattle)
        }

        this.lastUpdated = new Date()
        return cattle
      } catch (error) {
        this.error = error.message
        console.error('Failed to fetch cattle by ID:', error)
        throw error
      } finally {
        this.loading = false
      }
    },

    // Fetch cattle history
    async fetchCattleHistory(cattleId, limit = 100) {
      try {
        return await this.apiService.getCattleHistory(cattleId, limit)
      } catch (error) {
        console.error('Failed to fetch cattle history:', error)
        throw error
      }
    },

    // Create new cattle
    async createCattle(cattleData) {
      this.loading = true
      this.error = null

      try {
        const response = await this.apiService.createCattle(cattleData)
        const newCattle = this.apiService.transformCattleData([response])[0]
        this.cattleList.push(newCattle)
        this.lastUpdated = new Date()
        return newCattle
      } catch (error) {
        this.error = error.message
        console.error('Failed to create cattle:', error)
        throw error
      } finally {
        this.loading = false
      }
    },

    // Update cattle
    async updateCattle(cattleId, updateData) {
      this.loading = true
      this.error = null

      try {
        const response = await this.apiService.updateCattle(cattleId, updateData)
        const updatedCattle = this.apiService.transformCattleData([response])[0]

        // Update in list
        const index = this.cattleList.findIndex(c => c.id === cattleId)
        if (index >= 0) {
          this.cattleList[index] = updatedCattle
        }

        this.lastUpdated = new Date()
        return updatedCattle
      } catch (error) {
        this.error = error.message
        console.error('Failed to update cattle:', error)
        throw error
      } finally {
        this.loading = false
      }
    },

    // Delete cattle
    async deleteCattle(cattleId) {
      this.loading = true
      this.error = null

      try {
        await this.apiService.deleteCattle(cattleId)

        // Remove from list
        this.cattleList = this.cattleList.filter(c => c.id !== cattleId)

        // Clear selection if this cattle was selected
        if (this.selectedCattle?.id === cattleId) {
          this.selectedCattle = null
        }

        this.lastUpdated = new Date()
      } catch (error) {
        this.error = error.message
        console.error('Failed to delete cattle:', error)
        throw error
      } finally {
        this.loading = false
      }
    },

    // Update cattle position (from WebSocket)
    updateCattlePosition(cattleId, newLocation, geofenceStatus = null) {
      const index = this.cattleList.findIndex(c => c.id === cattleId)
      if (index >= 0) {
        this.cattleList[index].location = newLocation
        this.cattleList[index].lastUpdate = new Date().toISOString()

        if (geofenceStatus) {
          this.cattleList[index].geofenceStatus = geofenceStatus
        }

        this.lastUpdated = new Date()
      }
    },

    // Update cattle health status
    updateCattleHealth(cattleId, newHealthStatus) {
      const index = this.cattleList.findIndex(c => c.id === cattleId)
      if (index >= 0) {
        this.cattleList[index].healthStatus = newHealthStatus
        this.cattleList[index].lastUpdate = new Date().toISOString()
        this.lastUpdated = new Date()
      }
    },

    // Update multiple cattle (batch update from WebSocket)
    updateCattleData(cattleUpdates) {
      if (Array.isArray(cattleUpdates)) {
        cattleUpdates.forEach(update => {
          const index = this.cattleList.findIndex(c => c.id === update.id)
          if (index >= 0) {
            this.cattleList[index] = {
              ...this.cattleList[index],
              ...update,
              lastUpdate: new Date().toISOString()
            }
          }
        })
      }
      this.lastUpdated = new Date()
    },

    // Select cattle
    selectCattle(cattle) {
      this.selectedCattle = cattle
    },

    // Clear selection
    clearSelection() {
      this.selectedCattle = null
    },

    // Clear error
    clearError() {
      this.error = null
    },

    // Reset store
    resetStore() {
      this.cattleList = []
      this.selectedCattle = null
      this.loading = false
      this.error = null
      this.lastUpdated = null
    }
  }
})