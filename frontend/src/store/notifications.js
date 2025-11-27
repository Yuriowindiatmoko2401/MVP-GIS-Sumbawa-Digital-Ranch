/**
 * Notifications Store - Manages application notifications and alerts
 */

import { defineStore } from 'pinia'

export const useNotificationStore = defineStore('notifications', {
  state: () => ({
    notifications: [],
    maxNotifications: 100,
    autoRemoveDelay: 10000, // 10 seconds
    soundEnabled: true
  }),

  getters: {
    // Get unread notifications
    unreadNotifications: (state) => {
      return state.notifications.filter(notification => !notification.read)
    },

    // Get unread count
    unreadCount: (state) => {
      return state.notifications.filter(notification => !notification.read).length
    },

    // Get notifications by type
    getNotificationsByType: (state) => (type) => {
      return state.notifications.filter(notification => notification.type === type)
    },

    // Get recent notifications (last 24 hours)
    recentNotifications: (state) => {
      const twentyFourHoursAgo = new Date(Date.now() - 24 * 60 * 60 * 1000)
      return state.notifications.filter(
        notification => new Date(notification.timestamp) >= twentyFourHoursAgo
      )
    },

    // Get violation alerts
    violationAlerts: (state) => {
      return state.notifications.filter(notification => notification.type === 'violation')
    },

    // Get system notifications
    systemNotifications: (state) => {
      return state.notifications.filter(notification => notification.type === 'system')
    },

    // Get success notifications
    successNotifications: (state) => {
      return state.notifications.filter(notification => notification.type === 'success')
    },

    // Get warning notifications
    warningNotifications: (state) => {
      return state.notifications.filter(notification => notification.type === 'warning')
    },

    // Get error notifications
    errorNotifications: (state) => {
      return state.notifications.filter(notification => notification.type === 'error')
    }
  },

  actions: {
    // Add new notification
    addNotification(notificationData) {
      const notification = {
        id: Date.now() + Math.random(), // Simple unique ID
        type: notificationData.type || 'info',
        title: notificationData.title || 'Notification',
        message: notificationData.message || '',
        timestamp: notificationData.timestamp || new Date().toISOString(),
        read: false,
        autoRemove: notificationData.autoRemove !== false, // Default to true
        priority: notificationData.priority || 'normal',
        data: notificationData.data || null, // Additional data
        actions: notificationData.actions || [], // Action buttons
        duration: notificationData.duration || this.autoRemoveDelay
      }

      // Add to beginning of array (newest first)
      this.notifications.unshift(notification)

      // Limit number of notifications
      if (this.notifications.length > this.maxNotifications) {
        this.notifications = this.notifications.slice(0, this.maxNotifications)
      }

      // Auto-remove if enabled
      if (notification.autoRemove) {
        setTimeout(() => {
          this.removeNotification(notification.id)
        }, notification.duration)
      }

      // Play notification sound if enabled and not silent type
      if (this.soundEnabled && this.shouldPlaySound(notification.type)) {
        this.playNotificationSound(notification.type)
      }

      return notification
    },

    // Remove notification by ID
    removeNotification(notificationId) {
      const index = this.notifications.findIndex(n => n.id === notificationId)
      if (index >= 0) {
        this.notifications.splice(index, 1)
      }
    },

    // Mark notification as read
    markAsRead(notificationId) {
      const notification = this.notifications.find(n => n.id === notificationId)
      if (notification) {
        notification.read = true
      }
    },

    // Mark all notifications as read
    markAllAsRead() {
      this.notifications.forEach(notification => {
        notification.read = true
      })
    },

    // Clear all notifications
    clearNotifications() {
      this.notifications = []
    },

    // Clear notifications by type
    clearNotificationsByType(type) {
      this.notifications = this.notifications.filter(
        notification => notification.type !== type
      )
    },

    // Clear read notifications
    clearReadNotifications() {
      this.notifications = this.notifications.filter(
        notification => !notification.read
      )
    },

    // Clear old notifications (older than specified hours)
    clearOldNotifications(hours = 24) {
      const cutoffTime = new Date(Date.now() - hours * 60 * 60 * 1000)
      this.notifications = this.notifications.filter(
        notification => new Date(notification.timestamp) >= cutoffTime
      )
    },

    // Update notification
    updateNotification(notificationId, updateData) {
      const notification = this.notifications.find(n => n.id === notificationId)
      if (notification) {
        Object.assign(notification, updateData)
      }
    },

    // Add violation alert (convenience method)
    addViolationAlert(cattleIdentifier, location, geofenceName = null) {
      return this.addNotification({
        type: 'violation',
        title: '🚨 Geofence Violation',
        message: `Cattle ${cattleIdentifier} has left the ${geofenceName || 'designated area'}`,
        priority: 'high',
        autoRemove: false, // Don't auto-remove violation alerts
        data: {
          cattleIdentifier,
          location,
          geofenceName,
          violationType: 'LEFT_GEOFENCE'
        },
        actions: [
          {
            label: 'View Cattle',
            action: 'view_cattle',
            data: { cattleIdentifier }
          },
          {
            label: 'Dismiss',
            action: 'dismiss',
            style: 'secondary'
          }
        ]
      })
    },

    // Add system notification (convenience method)
    addSystemNotification(message, priority = 'normal') {
      return this.addNotification({
        type: 'system',
        title: '🔔 System Notification',
        message: message,
        priority: priority
      })
    },

    // Add success notification (convenience method)
    addSuccessNotification(title, message) {
      return this.addNotification({
        type: 'success',
        title: `✅ ${title}`,
        message: message,
        priority: 'low'
      })
    },

    // Add warning notification (convenience method)
    addWarningNotification(title, message) {
      return this.addNotification({
        type: 'warning',
        title: `⚠️ ${title}`,
        message: message,
        priority: 'normal'
      })
    },

    // Add error notification (convenience method)
    addErrorNotification(title, message) {
      return this.addNotification({
        type: 'error',
        title: `❌ ${title}`,
        message: message,
        priority: 'high',
        autoRemove: false
      })
    },

    // Add connection notification (convenience method)
    addConnectionNotification(status, details = null) {
      let title, message, type

      switch (status) {
        case 'connected':
          title = '🟢 Connected'
          message = 'Real-time connection established'
          type = 'success'
          break
        case 'disconnected':
          title = '🔴 Disconnected'
          message = 'Real-time connection lost. Attempting to reconnect...'
          type = 'warning'
          break
        case 'connecting':
          title = '🟡 Connecting'
          message = 'Establishing real-time connection...'
          type = 'info'
          break
        default:
          title = '🔵 Connection Status'
          message = `Connection status: ${status}`
          type = 'info'
      }

      return this.addNotification({
        type: type,
        title: title,
        message: message,
        priority: status === 'connected' ? 'low' : 'normal',
        data: { status, details }
      })
    },

    // Determine if sound should play for notification type
    shouldPlaySound(type) {
      const silentTypes = ['info', 'success']
      return !silentTypes.includes(type)
    },

    // Play notification sound
    playNotificationSound(type) {
      try {
        // Create audio context for notification sounds
        const audioContext = new (window.AudioContext || window.webkitAudioContext)()
        const oscillator = audioContext.createOscillator()
        const gainNode = audioContext.createGain()

        // Different sounds for different types
        switch (type) {
          case 'violation':
          case 'error':
            oscillator.frequency.value = 800 // High frequency
            gainNode.gain.value = 0.3
            break
          case 'warning':
            oscillator.frequency.value = 600
            gainNode.gain.value = 0.2
            break
          default:
            oscillator.frequency.value = 400
            gainNode.gain.value = 0.1
        }

        oscillator.connect(gainNode)
        gainNode.connect(audioContext.destination)

        oscillator.start()
        oscillator.stop(audioContext.currentTime + 0.2) // Short beep
      } catch (error) {
        console.warn('Could not play notification sound:', error)
      }
    },

    // Toggle sound
    toggleSound() {
      this.soundEnabled = !this.soundEnabled
    },

    // Set auto-remove delay
    setAutoRemoveDelay(delay) {
      this.autoRemoveDelay = delay
    },

    // Set max notifications
    setMaxNotifications(max) {
      this.maxNotifications = max
      // Trim notifications if needed
      if (this.notifications.length > max) {
        this.notifications = this.notifications.slice(0, max)
      }
    }
  }
})