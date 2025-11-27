/**
 * API Service for HTTP communication with FastAPI backend
 * Provides methods to fetch cattle, resources, geofences, and heatmap data
 */

import axios from 'axios'

class APIService {
  constructor() {
    this.baseURL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
    this.client = axios.create({
      baseURL: this.baseURL,
      timeout: 10000,
      headers: {
        'Content-Type': 'application/json'
      }
    })

    // Request interceptor
    this.client.interceptors.request.use(
      (config) => {
        console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`)
        return config
      },
      (error) => {
        console.error('API Request Error:', error)
        return Promise.reject(error)
      }
    )

    // Response interceptor
    this.client.interceptors.response.use(
      (response) => {
        console.log(`API Response: ${response.status} ${response.config.url}`)
        return response
      },
      (error) => {
        console.error('API Response Error:', error.response?.data || error.message)
        return Promise.reject(error)
      }
    )
  }

  // Generic HTTP methods
  async get(endpoint, params = {}) {
    try {
      const response = await this.client.get(endpoint, { params })
      return response.data
    } catch (error) {
      throw this.handleError(error)
    }
  }

  async post(endpoint, data = {}) {
    try {
      const response = await this.client.post(endpoint, data)
      return response.data
    } catch (error) {
      throw this.handleError(error)
    }
  }

  async put(endpoint, data = {}) {
    try {
      const response = await this.client.put(endpoint, data)
      return response.data
    } catch (error) {
      throw this.handleError(error)
    }
  }

  async delete(endpoint) {
    try {
      const response = await this.client.delete(endpoint)
      return response.data
    } catch (error) {
      throw this.handleError(error)
    }
  }

  handleError(error) {
    if (error.response) {
      // Server responded with error status
      const { status, data } = error.response
      return new Error(data.detail || data.message || `HTTP ${status} Error`)
    } else if (error.request) {
      // Request was made but no response received
      return new Error('Network error - no response from server')
    } else {
      // Something else happened
      return new Error(error.message || 'Unknown API error')
    }
  }

  // Health check
  async healthCheck() {
    return this.get('/api/health')
  }

  // Cattle endpoints
  async getCattle() {
    return this.get('/api/cattle')
  }

  async getCattleById(cattleId) {
    return this.get(`/api/cattle/${cattleId}`)
  }

  async getCattleHistory(cattleId, limit = 100) {
    return this.get(`/api/cattle/history/${cattleId}`, { limit })
  }

  async updateCattle(cattleId, data) {
    return this.put(`/api/cattle/${cattleId}`, data)
  }

  async createCattle(data) {
    return this.post('/api/cattle', data)
  }

  async deleteCattle(cattleId) {
    return this.delete(`/api/cattle/${cattleId}`)
  }

  // Resource endpoints
  async getResources() {
    return this.get('/api/resources')
  }

  async getResourcesByType(resourceType) {
    return this.get(`/api/resources/${resourceType}`)
  }

  async createResource(data) {
    return this.post('/api/resources', data)
  }

  async updateResource(resourceId, data) {
    return this.put(`/api/resources/${resourceId}`, data)
  }

  async deleteResource(resourceId) {
    return this.delete(`/api/resources/${resourceId}`)
  }

  // Geofence endpoints
  async getGeofences() {
    return this.get('/api/geofences')
  }

  async getGeofenceById(geofenceId) {
    return this.get(`/api/geofences/${geofenceId}`)
  }

  async createGeofence(data) {
    return this.post('/api/geofences', data)
  }

  async updateGeofence(geofenceId, data) {
    return this.put(`/api/geofences/${geofenceId}`, data)
  }

  async deleteGeofence(geofenceId) {
    return this.delete(`/api/geofences/${geofenceId}`)
  }

  async checkCattleInGeofence(cattleId, geofenceId) {
    return this.get(`/api/geofences/${geofenceId}/check/${cattleId}`)
  }

  // Heatmap endpoints
  async getHeatmapData(hours = 24) {
    return this.get('/api/heatmap', { hours })
  }

  // Statistics endpoints
  async getStatistics() {
    return this.get('/api/stats')
  }

  async getCattleStats() {
    return this.get('/api/stats/cattle')
  }

  async getResourceStats() {
    return this.get('/api/stats/resources')
  }

  // Utility methods for data transformation
  transformCattleData(cattleArray) {
    return cattleArray.map(cattle => ({
      id: cattle.id,
      identifier: cattle.identifier,
      age: cattle.age,
      healthStatus: cattle.health_status,
      location: cattle.location,
      lastUpdate: cattle.last_update,
      geofenceStatus: this.calculateGeofenceStatus(cattle)
    }))
  }

  transformResourceData(resourcesArray) {
    return resourcesArray.map(resource => ({
      id: resource.id,
      type: resource.resource_type,
      name: resource.name,
      location: resource.location,
      capacity: resource.capacity || null,
      currentUsage: resource.current_usage || 0
    }))
  }

  transformGeofenceData(geofencesArray) {
    return geofencesArray.map(geofence => ({
      id: geofence.id,
      name: geofence.name,
      boundary: geofence.boundary,
      createdAt: geofence.created_at,
      cattleCount: geofence.cattle_count || 0
    }))
  }

  calculateGeofenceStatus(cattle) {
    // This would be calculated on the backend normally
    // For now, assume all cattle are within geofence
    return 'within'
  }
}

// Create a singleton instance
const apiService = new APIService()

// Export as a composable for Vue 3
export function useAPIService() {
  return {
    client: apiService.client,
    baseURL: apiService.baseURL,
    get: (endpoint, params) => apiService.get(endpoint, params),
    post: (endpoint, data) => apiService.post(endpoint, data),
    put: (endpoint, data) => apiService.put(endpoint, data),
    delete: (endpoint) => apiService.delete(endpoint),
    healthCheck: () => apiService.healthCheck(),
    getCattle: () => apiService.getCattle(),
    getCattleById: (id) => apiService.getCattleById(id),
    getCattleHistory: (id, limit) => apiService.getCattleHistory(id, limit),
    updateCattle: (id, data) => apiService.updateCattle(id, data),
    createCattle: (data) => apiService.createCattle(data),
    deleteCattle: (id) => apiService.deleteCattle(id),
    getResources: () => apiService.getResources(),
    getResourcesByType: (type) => apiService.getResourcesByType(type),
    createResource: (data) => apiService.createResource(data),
    updateResource: (id, data) => apiService.updateResource(id, data),
    deleteResource: (id) => apiService.deleteResource(id),
    getGeofences: () => apiService.getGeofences(),
    getGeofenceById: (id) => apiService.getGeofenceById(id),
    createGeofence: (data) => apiService.createGeofence(data),
    updateGeofence: (id, data) => apiService.updateGeofence(id, data),
    deleteGeofence: (id) => apiService.deleteGeofence(id),
    checkCattleInGeofence: (cattleId, geofenceId) => apiService.checkCattleInGeofence(cattleId, geofenceId),
    getHeatmapData: (hours) => apiService.getHeatmapData(hours),
    getStatistics: () => apiService.getStatistics(),
    getCattleStats: () => apiService.getCattleStats(),
    getResourceStats: () => apiService.getResourceStats(),
    transformCattleData: (data) => apiService.transformCattleData(data),
    transformResourceData: (data) => apiService.transformResourceData(data),
    transformGeofenceData: (data) => apiService.transformGeofenceData(data)
  }
}

export default apiService