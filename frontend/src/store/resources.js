/**
 * Resources Store - Manages resource data (water troughs, feeding stations, shelters)
 */

import { defineStore } from 'pinia'
import { useAPIService } from '@/services/apiService'

export const useResourceStore = defineStore('resources', {
  state: () => ({
    resources: [],
    selectedResource: null,
    loading: false,
    error: null,
    lastUpdated: null,
    filters: {
      resourceType: null, // 'water_trough', 'feeding_station', 'shelter', null for all
      showActiveOnly: true
    }
  }),

  getters: {
    // Get resources filtered by type
    getResourcesByType: (state) => (resourceType) => {
      if (!resourceType) return state.resources
      return state.resources.filter(resource => resource.type === resourceType)
    },

    // Get water troughs
    waterTroughs: (state) => {
      return state.resources.filter(resource => resource.type === 'water_trough')
    },

    // Get feeding stations
    feedingStations: (state) => {
      return state.resources.filter(resource => resource.type === 'feeding_station')
    },

    // Get shelters
    shelters: (state) => {
      return state.resources.filter(resource => resource.type === 'shelter')
    },

    // Get filtered resources based on current filters
    filteredResources: (state) => {
      let filtered = [...state.resources]

      // Filter by type
      if (state.filters.resourceType) {
        filtered = filtered.filter(resource => resource.type === state.filters.resourceType)
      }

      // Filter by active status
      if (state.filters.showActiveOnly) {
        filtered = filtered.filter(resource => resource.isActive !== false)
      }

      return filtered
    },

    // Get statistics
    statistics: (state) => {
      return {
        total: state.resources.length,
        waterTroughs: state.resources.filter(r => r.type === 'water_trough').length,
        feedingStations: state.resources.filter(r => r.type === 'feeding_station').length,
        shelters: state.resources.filter(r => r.type === 'shelter').length,
        totalCapacity: state.resources.reduce((sum, r) => sum + (r.capacity || 0), 0),
        totalUsage: state.resources.reduce((sum, r) => sum + (r.currentUsage || 0), 0),
        utilizationRate: state.resources.length > 0
          ? (state.resources.reduce((sum, r) => sum + (r.currentUsage || 0), 0) /
             state.resources.reduce((sum, r) => sum + (r.capacity || 0), 0)) * 100
          : 0
      }
    }
  },

  actions: {
    // API Service
    apiService: useAPIService(),

    // Fetch all resources
    async fetchResources() {
      this.loading = true
      this.error = null

      try {
        const response = await this.apiService.getResources()
        this.resources = this.apiService.transformResourceData(response)
        this.lastUpdated = new Date()
      } catch (error) {
        this.error = error.message
        console.error('Failed to fetch resources:', error)
        throw error
      } finally {
        this.loading = false
      }
    },

    // Fetch resources by type
    async fetchResourcesByType(resourceType) {
      this.loading = true
      this.error = null

      try {
        const response = await this.apiService.getResourcesByType(resourceType)
        const resourcesByType = this.apiService.transformResourceData(response)

        // Update resources list (remove existing of this type, add new ones)
        this.resources = [
          ...this.resources.filter(r => r.type !== resourceType),
          ...resourcesByType
        ]

        this.lastUpdated = new Date()
        return resourcesByType
      } catch (error) {
        this.error = error.message
        console.error('Failed to fetch resources by type:', error)
        throw error
      } finally {
        this.loading = false
      }
    },

    // Create new resource
    async createResource(resourceData) {
      this.loading = true
      this.error = null

      try {
        const response = await this.apiService.createResource(resourceData)
        const newResource = this.apiService.transformResourceData([response])[0]
        this.resources.push(newResource)
        this.lastUpdated = new Date()
        return newResource
      } catch (error) {
        this.error = error.message
        console.error('Failed to create resource:', error)
        throw error
      } finally {
        this.loading = false
      }
    },

    // Update resource
    async updateResource(resourceId, updateData) {
      this.loading = true
      this.error = null

      try {
        const response = await this.apiService.updateResource(resourceId, updateData)
        const updatedResource = this.apiService.transformResourceData([response])[0]

        // Update in list
        const index = this.resources.findIndex(r => r.id === resourceId)
        if (index >= 0) {
          this.resources[index] = updatedResource
        }

        this.lastUpdated = new Date()
        return updatedResource
      } catch (error) {
        this.error = error.message
        console.error('Failed to update resource:', error)
        throw error
      } finally {
        this.loading = false
      }
    },

    // Delete resource
    async deleteResource(resourceId) {
      this.loading = true
      this.error = null

      try {
        await this.apiService.deleteResource(resourceId)

        // Remove from list
        this.resources = this.resources.filter(r => r.id !== resourceId)

        // Clear selection if this resource was selected
        if (this.selectedResource?.id === resourceId) {
          this.selectedResource = null
        }

        this.lastUpdated = new Date()
      } catch (error) {
        this.error = error.message
        console.error('Failed to delete resource:', error)
        throw error
      } finally {
        this.loading = false
      }
    },

    // Update resource usage (from WebSocket or local updates)
    updateResourceUsage(resourceId, newUsage) {
      const index = this.resources.findIndex(r => r.id === resourceId)
      if (index >= 0) {
        this.resources[index].currentUsage = newUsage
        this.resources[index].lastUpdate = new Date().toISOString()
        this.lastUpdated = new Date()
      }
    },

    // Set resource active/inactive status
    setResourceStatus(resourceId, isActive) {
      const index = this.resources.findIndex(r => r.id === resourceId)
      if (index >= 0) {
        this.resources[index].isActive = isActive
        this.resources[index].lastUpdate = new Date().toISOString()
        this.lastUpdated = new Date()
      }
    },

    // Select resource
    selectResource(resource) {
      this.selectedResource = resource
    },

    // Clear selection
    clearSelection() {
      this.selectedResource = null
    },

    // Set filters
    setFilters(newFilters) {
      this.filters = {
        ...this.filters,
        ...newFilters
      }
    },

    // Clear filters
    clearFilters() {
      this.filters = {
        resourceType: null,
        showActiveOnly: true
      }
    },

    // Clear error
    clearError() {
      this.error = null
    },

    // Reset store
    resetStore() {
      this.resources = []
      this.selectedResource = null
      this.loading = false
      this.error = null
      this.lastUpdated = null
      this.filters = {
        resourceType: null,
        showActiveOnly: true
      }
    }
  }
})