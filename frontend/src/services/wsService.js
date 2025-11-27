/**
 * WebSocket Service for real-time communication with backend
 * Handles cattle updates, violation alerts, and heatmap data
 */

import { ref } from 'vue'

class WebSocketService {
  constructor() {
    this.url = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws'
    this.ws = null
    this.connectionStatus = ref('disconnected')
    this.listeners = new Map()
    this.reconnectAttempts = 0
    this.maxReconnectAttempts = 5
    this.reconnectDelay = 1000
    this.heartbeatInterval = null
  }

  connect() {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      return Promise.resolve()
    }

    return new Promise((resolve, reject) => {
      try {
        this.connectionStatus.value = 'connecting'
        this.ws = new WebSocket(this.url)

        this.ws.onopen = () => {
          console.log('WebSocket connected to:', this.url)
          this.connectionStatus.value = 'connected'
          this.reconnectAttempts = 0
          this.startHeartbeat()
          this.emit('connectionChange', 'connected')
          resolve()
        }

        this.ws.onmessage = (event) => {
          try {
            const message = JSON.parse(event.data)
            this.emit('message', message)
          } catch (error) {
            console.error('Failed to parse WebSocket message:', error)
          }
        }

        this.ws.onerror = (error) => {
          console.error('WebSocket error:', error)
          this.connectionStatus.value = 'disconnected'
          this.emit('connectionChange', 'disconnected')
          reject(error)
        }

        this.ws.onclose = (event) => {
          console.log('WebSocket disconnected:', event.code, event.reason)
          this.connectionStatus.value = 'disconnected'
          this.stopHeartbeat()
          this.emit('connectionChange', 'disconnected')

          // Attempt to reconnect
          if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.attemptReconnect()
          }
        }
      } catch (error) {
        console.error('Failed to create WebSocket connection:', error)
        reject(error)
      }
    })
  }

  disconnect() {
    this.stopHeartbeat()
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
    this.connectionStatus.value = 'disconnected'
  }

  send(message) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message))
      return true
    }
    console.warn('WebSocket not connected, message not sent:', message)
    return false
  }

  on(eventType, callback) {
    if (!this.listeners.has(eventType)) {
      this.listeners.set(eventType, [])
    }
    this.listeners.get(eventType).push(callback)
  }

  off(eventType, callback) {
    if (this.listeners.has(eventType)) {
      const callbacks = this.listeners.get(eventType)
      const index = callbacks.indexOf(callback)
      if (index > -1) {
        callbacks.splice(index, 1)
      }
    }
  }

  emit(eventType, data) {
    if (this.listeners.has(eventType)) {
      this.listeners.get(eventType).forEach(callback => {
        try {
          callback(data)
        } catch (error) {
          console.error('Error in WebSocket event listener:', error)
        }
      })
    }
  }

  attemptReconnect() {
    this.reconnectAttempts++
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1)

    console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts}) in ${delay}ms...`)

    setTimeout(() => {
      this.connect().catch(error => {
        console.error('Reconnection failed:', error)
      })
    }, delay)
  }

  startHeartbeat() {
    this.heartbeatInterval = setInterval(() => {
      this.send({ type: 'heartbeat', timestamp: Date.now() })
    }, 30000) // Send heartbeat every 30 seconds
  }

  stopHeartbeat() {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval)
      this.heartbeatInterval = null
    }
  }

  // Utility methods for specific message types
  requestCattleUpdate() {
    this.send({ type: 'request_cattle_update' })
  }

  requestHeatmapData(hours = 24) {
    this.send({ type: 'request_heatmap', hours })
  }

  subscribeToViolations() {
    this.send({ type: 'subscribe_violations' })
  }

  unsubscribeFromViolations() {
    this.send({ type: 'unsubscribe_violations' })
  }
}

// Create a singleton instance
const wsService = new WebSocketService()

// Export as a composable for Vue 3
export function useWebSocketService() {
  return {
    wsService,
    connectionStatus: wsService.connectionStatus,
    connect: () => wsService.connect(),
    disconnect: () => wsService.disconnect(),
    send: (message) => wsService.send(message),
    on: (eventType, callback) => wsService.on(eventType, callback),
    off: (eventType, callback) => wsService.off(eventType, callback),
    requestCattleUpdate: () => wsService.requestCattleUpdate(),
    requestHeatmapData: (hours) => wsService.requestHeatmapData(hours),
    subscribeToViolations: () => wsService.subscribeToViolations(),
    unsubscribeFromViolations: () => wsService.unsubscribeFromViolations()
  }
}

export default wsService