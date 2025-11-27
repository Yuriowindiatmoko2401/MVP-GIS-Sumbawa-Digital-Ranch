/**
 * Geofences Store - Manages geofence data and boundary definitions
 */

import { defineStore } from 'pinia'
import { useAPIService } from '@/services/apiService'

export const useGeofenceStore = defineStore('geofences', {
  state: () => ({
    geofences: [],
    selectedGeofence: null,
    activeGeofence: null, // Primary geofence for cattle tracking
    loading: false,
    error: null,
    lastUpdated: null
  }),

  getters: {
    // Get geofence by ID
    getGeofenceById: (state) => (id) => {
      return state.geofences.find(geofence => geofence.id === id)
    },

    // Get geofence by name
    getGeofenceByName: (state) => (name) => {
      return state.geofences.find(geofence => geofence.name === name)
    },

    // Get total area of all geofences
    totalArea: (state) => {
      return state.geofences.reduce((total, geofence) => total + (geofence.area || 0), 0)
    },

    // Get statistics
    statistics: (state) => {
      return {
        total: state.geofences.length,
        active: state.geofences.filter(g => g.isActive !== false).length,
        totalArea: state.geofences.reduce((sum, g) => sum + (g.area || 0), 0),
        totalCattle: state.geofences.reduce((sum, g) => sum + (g.cattleCount || 0), 0)
      }
    }
  },

  actions: {
    // API Service
    apiService: useAPIService(),

    // Fetch all geofences
    async fetchGeofences() {
      this.loading = true
      this.error = null

      try {
        const response = await this.apiService.getGeofences()
        this.geofences = this.apiService.transformGeofenceData(response)

        // Set first geofence as active if none selected
        if (this.geofences.length > 0 && !this.activeGeofence) {
          this.activeGeofence = this.geofences[0]
        }

        this.lastUpdated = new Date()
      } catch (error) {
        this.error = error.message
        console.error('Failed to fetch geofences:', error)
        throw error
      } finally {
        this.loading = false
      }
    },

    // Fetch geofence by ID
    async fetchGeofenceById(geofenceId) {
      this.loading = true
      this.error = null

      try {
        const response = await this.apiService.getGeofenceById(geofenceId)
        const geofence = this.apiService.transformGeofenceData([response])[0]

        // Update or add to list
        const existingIndex = this.geofences.findIndex(g => g.id === geofenceId)
        if (existingIndex >= 0) {
          this.geofences[existingIndex] = geofence
        } else {
          this.geofences.push(geofence)
        }

        this.lastUpdated = new Date()
        return geofence
      } catch (error) {
        this.error = error.message
        console.error('Failed to fetch geofence by ID:', error)
        throw error
      } finally {
        this.loading = false
      }
    },

    // Create new geofence
    async createGeofence(geofenceData) {
      this.loading = true
      this.error = null

      try {
        const response = await this.apiService.createGeofence(geofenceData)
        const newGeofence = this.apiService.transformGeofenceData([response])[0]
        this.geofences.push(newGeofence)

        // Set as active if it's the first geofence
        if (this.geofences.length === 1) {
          this.activeGeofence = newGeofence
        }

        this.lastUpdated = new Date()
        return newGeofence
      } catch (error) {
        this.error = error.message
        console.error('Failed to create geofence:', error)
        throw error
      } finally {
        this.loading = false
      }
    },

    // Update geofence
    async updateGeofence(geofenceId, updateData) {
      this.loading = true
      this.error = null

      try {
        const response = await this.apiService.updateGeofence(geofenceId, updateData)
        const updatedGeofence = this.apiService.transformGeofenceData([response])[0]

        // Update in list
        const index = this.geofences.findIndex(g => g.id === geofenceId)
        if (index >= 0) {
          this.geofences[index] = updatedGeofence

          // Update active geofence if it was the one updated
          if (this.activeGeofence?.id === geofenceId) {
            this.activeGeofence = updatedGeofence
          }
        }

        this.lastUpdated = new Date()
        return updatedGeofence
      } catch (error) {
        this.error = error.message
        console.error('Failed to update geofence:', error)
        throw error
      } finally {
        this.loading = false
      }
    },

    // Delete geofence
    async deleteGeofence(geofenceId) {
      this.loading = true
      this.error = null

      try {
        await this.apiService.deleteGeofence(geofenceId)

        // Remove from list
        this.geofences = this.geofences.filter(g => g.id !== geofenceId)

        // Clear selection and update active geofence
        if (this.selectedGeofence?.id === geofenceId) {
          this.selectedGeofence = null
        }

        if (this.activeGeofence?.id === geofenceId) {
          // Set new active geofence or null if no geofences left
          this.activeGeofence = this.geofences.length > 0 ? this.geofences[0] : null
        }

        this.lastUpdated = new Date()
      } catch (error) {
        this.error = error.message
        console.error('Failed to delete geofence:', error)
        throw error
      } finally {
        this.loading = false
      }
    },

    // Check if cattle is within geofence
    async checkCattleInGeofence(cattleId, geofenceId) {
      try {
        return await this.apiService.checkCattleInGeofence(cattleId, geofenceId)
      } catch (error) {
        console.error('Failed to check cattle geofence status:', error)
        throw error
      }
    },

    // Update geofence cattle count
    updateGeofenceCattleCount(geofenceId, count) {
      const index = this.geofences.findIndex(g => g.id === geofenceId)
      if (index >= 0) {
        this.geofences[index].cattleCount = count
        this.geofences[index].lastUpdate = new Date().toISOString()
        this.lastUpdated = new Date()
      }
    },

    // Set active geofence
    setActiveGeofence(geofence) {
      this.activeGeofence = geofence
    },

    // Select geofence
    selectGeofence(geofence) {
      this.selectedGeofence = geofence
    },

    // Clear selection
    clearSelection() {
      this.selectedGeofence = null
    },

    // Clear error
    clearError() {
      this.error = null
    },

    // Reset store
    resetStore() {
      this.geofences = []
      this.selectedGeofence = null
      this.activeGeofence = null
      this.loading = false
      this.error = null
      this.lastUpdated = null
    }
  }
})