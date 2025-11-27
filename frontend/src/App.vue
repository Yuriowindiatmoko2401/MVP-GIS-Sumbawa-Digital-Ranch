<template>
  <div class="app-container">
    <!-- Header -->
    <header class="app-header">
      <div class="header-content">
        <div class="logo-section">
          <h1 class="app-title">
            🐄 Sumbawa Digital Ranch
          </h1>
          <span class="app-subtitle">GIS Dashboard</span>
        </div>

        <div class="status-section">
          <div class="connection-status" :class="connectionStatusClass">
            <span class="status-indicator"></span>
            <span class="status-text">{{ connectionStatusText }}</span>
          </div>
          <div class="last-update" v-if="lastUpdateTime">
            Last Update: {{ formatTime(lastUpdateTime) }}
          </div>
        </div>
      </div>
    </header>

    <!-- Main Content -->
    <div class="app-content">
      <!-- Sidebar -->
      <aside class="sidebar" :class="{ 'sidebar-collapsed': sidebarCollapsed }">
        <div class="sidebar-header">
          <button
            class="sidebar-toggle"
            @click="toggleSidebar"
            :title="sidebarCollapsed ? 'Expand Sidebar' : 'Collapse Sidebar'"
          >
            <i class="fas" :class="sidebarCollapsed ? 'fa-chevron-right' : 'fa-chevron-left'"></i>
          </button>
          <h3 v-if="!sidebarCollapsed">Controls</h3>
        </div>

        <div class="sidebar-content">
          <!-- Layer Control -->
          <LayerControl v-if="!sidebarCollapsed" @layer-toggle="handleLayerToggle" />

          <!-- Quick Stats -->
          <div v-if="!sidebarCollapsed" class="quick-stats">
            <h4>Quick Stats</h4>
            <div class="stat-item">
              <span class="stat-label">Total Cattle:</span>
              <span class="stat-value">{{ cattleCount }}</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">Violations:</span>
              <span class="stat-value" :class="{ 'text-danger': violationsCount > 0 }">
                {{ violationsCount }}
              </span>
            </div>
            <div class="stat-item">
              <span class="stat-label">Resources:</span>
              <span class="stat-value">{{ resourceCount }}</span>
            </div>
          </div>

          <!-- Action Buttons -->
          <div v-if="!sidebarCollapsed" class="action-buttons">
            <button
              class="btn btn-primary btn-sm mb-2"
              @click="refreshData"
              :disabled="loading"
            >
              <i class="fas fa-sync-alt"></i>
              Refresh Data
            </button>
            <button
              class="btn btn-secondary btn-sm"
              @click="toggleHeatmap"
              :class="{ active: showHeatmap }"
            >
              <i class="fas fa-fire"></i>
              {{ showHeatmap ? 'Hide' : 'Show' }} Heatmap
            </button>
          </div>
        </div>
      </aside>

      <!-- Map Container -->
      <main class="map-container">
        <MapViewer
          ref="mapViewer"
          :layers-visible="layersVisible"
          :show-heatmap="showHeatmap"
          :cattle-data="cattleData"
          :resource-data="resourceData"
          :geofence-data="geofenceData"
          @map-ready="handleMapReady"
          @cattle-click="handleCattleClick"
          @resource-click="handleResourceClick"
          @geofence-click="handleGeofenceClick"
        />

        <!-- Loading Overlay -->
        <div v-if="loading" class="loading-overlay">
          <div class="loading-content">
            <div class="spinner"></div>
            <p>Loading map data...</p>
          </div>
        </div>
      </main>

      <!-- Notification Panel -->
      <aside class="notification-panel">
        <NotificationPanel
          ref="notificationPanel"
          :notifications="notifications"
          @clear-notification="handleClearNotification"
          @clear-all="handleClearAllNotifications"
        />
      </aside>
    </div>

    <!-- Cattle Details Modal -->
    <CattleDetailsModal
      v-if="selectedCattle"
      :cattle="selectedCattle"
      @close="selectedCattle = null"
    />

    <!-- Error Toast -->
    <div v-if="error" class="error-toast">
      <div class="error-content">
        <i class="fas fa-exclamation-triangle"></i>
        <span>{{ error }}</span>
        <button @click="clearError" class="close-btn">
          <i class="fas fa-times"></i>
        </button>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useCattleStore } from '@/store/cattle'
import { useResourceStore } from '@/store/resources'
import { useGeofenceStore } from '@/store/geofences'
import { useNotificationStore } from '@/store/notifications'
import { useWebSocketService } from '@/services/wsService'
import LayerControl from '@/components/LayerControl.vue'
import MapViewer from '@/components/MapViewer.vue'
import NotificationPanel from '@/components/NotificationPanel.vue'
import CattleDetailsModal from '@/components/CattleDetailsModal.vue'

export default {
  name: 'App',
  components: {
    LayerControl,
    MapViewer,
    NotificationPanel,
    CattleDetailsModal
  },
  setup() {
    // Stores
    const cattleStore = useCattleStore()
    const resourceStore = useResourceStore()
    const geofenceStore = useGeofenceStore()
    const notificationStore = useNotificationStore()

    // WebSocket service
    const wsService = useWebSocketService()

    // Reactive state
    const sidebarCollapsed = ref(false)
    const loading = ref(false)
    const error = ref(null)
    const lastUpdateTime = ref(null)
    const selectedCattle = ref(null)

    // Layer visibility
    const layersVisible = ref({
      cattle: true,
      waterResources: true,
      feedResources: true,
      shelterResources: true,
      geofences: true,
      heatmap: false
    })

    const showHeatmap = ref(false)

    // Map viewer ref
    const mapViewer = ref(null)
    const notificationPanel = ref(null)

    // Computed properties
    const connectionStatus = computed(() => wsService.connectionStatus.value)
    const cattleData = computed(() => cattleStore.cattleList)
    const resourceData = computed(() => resourceStore.resources)
    const geofenceData = computed(() => geofenceStore.geofences)
    const notifications = computed(() => notificationStore.notifications)

    const cattleCount = computed(() => cattleStore.cattleList.length)
    const violationsCount = computed(() =>
      cattleStore.cattleList.filter(cattle => cattle.geofenceStatus === 'outside').length
    )
    const resourceCount = computed(() => resourceStore.resources.length)

    const connectionStatusClass = computed(() => {
      return {
        'connected': connectionStatus.value === 'connected',
        'disconnected': connectionStatus.value === 'disconnected',
        'connecting': connectionStatus.value === 'connecting'
      }
    })

    const connectionStatusText = computed(() => {
      switch (connectionStatus.value) {
        case 'connected':
          return '🟢 Connected'
        case 'connecting':
          return '🟡 Connecting...'
        case 'disconnected':
          return '🔴 Disconnected'
        default:
          return '⚪ Unknown'
      }
    })

    // Methods
    const formatTime = (date) => {
      if (!date) return 'Never'
      return new Intl.DateTimeFormat('en-US', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      }).format(new Date(date))
    }

    const toggleSidebar = () => {
      sidebarCollapsed.value = !sidebarCollapsed.value
    }

    const handleLayerToggle = (layerName, isVisible) => {
      layersVisible.value[layerName] = isVisible
    }

    const toggleHeatmap = () => {
      showHeatmap.value = !showHeatmap.value
      layersVisible.value.heatmap = showHeatmap.value
    }

    const refreshData = async () => {
      loading.value = true
      error.value = null

      try {
        await Promise.all([
          cattleStore.fetchCattle(),
          resourceStore.fetchResources(),
          geofenceStore.fetchGeofences()
        ])

        lastUpdateTime.value = new Date()

        // Refresh map if ready
        if (mapViewer.value && mapViewer.value.isMapReady) {
          await mapViewer.value.refreshLayers()
        }
      } catch (err) {
        error.value = `Failed to refresh data: ${err.message}`
        console.error('Refresh error:', err)
      } finally {
        loading.value = false
      }
    }

    const handleMapReady = async () => {
      console.log('Map is ready')
      // Initial data load
      await refreshData()
    }

    const handleCattleClick = (cattle) => {
      selectedCattle.value = cattle
    }

    const handleResourceClick = (resource) => {
      console.log('Resource clicked:', resource)
      // Could show resource details modal
    }

    const handleGeofenceClick = (geofence) => {
      console.log('Geofence clicked:', geofence)
      // Could show geofence details
    }

    const handleClearNotification = (notificationId) => {
      notificationStore.removeNotification(notificationId)
    }

    const handleClearAllNotifications = () => {
      notificationStore.clearNotifications()
    }

    const clearError = () => {
      error.value = null
    }

    // WebSocket event handlers
    const handleWebSocketMessage = async (message) => {
      console.log('WebSocket message received:', message)
      lastUpdateTime.value = new Date()

      switch (message.type) {
        case 'cattle_update':
          cattleStore.updateCattleData(message.data.cattle)
          break
        case 'violation_alert':
          notificationStore.addNotification({
            type: 'violation',
            title: 'Geofence Violation',
            message: `${message.data.alert.cattle_identifier} has left the geofenced area`,
            data: message.data.alert,
            timestamp: message.data.timestamp
          })
          break
        case 'heatmap_refresh':
          if (mapViewer.value && mapViewer.value.isMapReady) {
            await mapViewer.value.updateHeatmap(message.data.heatmap)
          }
          break
      }
    }

    const handleConnectionChange = (status) => {
      console.log('WebSocket connection status changed:', status)

      if (status === 'connected') {
        notificationStore.addNotification({
          type: 'success',
          title: 'Connected',
          message: 'Real-time connection established',
          timestamp: new Date().toISOString()
        })
      } else if (status === 'disconnected') {
        notificationStore.addNotification({
          type: 'warning',
          title: 'Disconnected',
          message: 'Real-time connection lost. Attempting to reconnect...',
          timestamp: new Date().toISOString()
        })
      }
    }

    // Lifecycle
    onMounted(async () => {
      // Initialize WebSocket
      wsService.connect()
      wsService.on('message', handleWebSocketMessage)
      wsService.on('connectionChange', handleConnectionChange)

      // Auto-refresh interval
      const refreshInterval = setInterval(() => {
        if (connectionStatus.value === 'connected') {
          refreshData()
        }
      }, 30000) // Refresh every 30 seconds

      // Store for cleanup
      window.refreshInterval = refreshInterval
    })

    onUnmounted(() => {
      // Cleanup WebSocket
      wsService.off('message', handleWebSocketMessage)
      wsService.off('connectionChange', handleConnectionChange)
      wsService.disconnect()

      // Clear auto-refresh
      if (window.refreshInterval) {
        clearInterval(window.refreshInterval)
      }
    })

    return {
      // Reactive data
      sidebarCollapsed,
      loading,
      error,
      lastUpdateTime,
      selectedCattle,
      layersVisible,
      showHeatmap,
      mapViewer,
      notificationPanel,

      // Computed
      connectionStatus,
      cattleData,
      resourceData,
      geofenceData,
      notifications,
      cattleCount,
      violationsCount,
      resourceCount,
      connectionStatusClass,
      connectionStatusText,

      // Methods
      formatTime,
      toggleSidebar,
      handleLayerToggle,
      toggleHeatmap,
      refreshData,
      handleMapReady,
      handleCattleClick,
      handleResourceClick,
      handleGeofenceClick,
      handleClearNotification,
      handleClearAllNotifications,
      clearError
    }
  }
}
</script>

<style lang="scss" scoped>
.app-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  width: 100vw;
  background-color: $background-color;
}

.app-header {
  background: white;
  border-bottom: 1px solid $border-color;
  box-shadow: $shadow-sm;
  z-index: $z-index-sticky;
  position: relative;

  .header-content {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: $spacing-sm $spacing-md;
    max-width: 100%;
    height: $header-height;
  }

  .logo-section {
    display: flex;
    align-items: baseline;
    gap: $spacing-xs;

    .app-title {
      font-size: $font-size-xl;
      font-weight: $font-weight-bold;
      color: $primary-color;
      margin: 0;
    }

    .app-subtitle {
      font-size: $font-size-sm;
      color: $text-muted;
      font-weight: $font-weight-medium;
    }
  }

  .status-section {
    display: flex;
    align-items: center;
    gap: $spacing-md;

    .connection-status {
      display: flex;
      align-items: center;
      gap: $spacing-xxs;
      padding: $spacing-xs $spacing-sm;
      border-radius: $border-radius;
      font-size: $font-size-sm;
      font-weight: $font-weight-medium;

      .status-indicator {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        display: inline-block;
      }

      &.connected {
        background-color: rgba($success-color, 0.1);
        color: $success-color;
        .status-indicator {
          background-color: $success-color;
        }
      }

      &.connecting {
        background-color: rgba($warning-color, 0.1);
        color: $warning-color;
        .status-indicator {
          background-color: $warning-color;
          animation: pulse 1.5s infinite;
        }
      }

      &.disconnected {
        background-color: rgba($danger-color, 0.1);
        color: $danger-color;
        .status-indicator {
          background-color: $danger-color;
        }
      }
    }

    .last-update {
      font-size: $font-size-xs;
      color: $text-muted;
      white-space: nowrap;
    }
  }
}

.app-content {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.sidebar {
  width: $sidebar-width;
  background: white;
  border-right: 1px solid $border-color;
  display: flex;
  flex-direction: column;
  transition: width 0.3s ease;
  z-index: $z-index-fixed;

  &.sidebar-collapsed {
    width: $sidebar-collapsed-width;
  }

  .sidebar-header {
    display: flex;
    align-items: center;
    padding: $spacing-sm;
    border-bottom: 1px solid $border-color;
    min-height: $header-height;

    .sidebar-toggle {
      background: none;
      border: 1px solid $border-color;
      border-radius: $border-radius;
      padding: $spacing-xs;
      cursor: pointer;
      transition: all $transition-base;

      &:hover {
        background-color: $gray-100;
        border-color: $gray-400;
      }
    }

    h3 {
      margin: 0;
      margin-left: $spacing-sm;
      font-size: $font-size-lg;
      color: $text-color;
    }
  }

  .sidebar-content {
    flex: 1;
    overflow-y: auto;
    padding: $spacing-sm;
  }

  .quick-stats {
    margin-top: $spacing-lg;

    h4 {
      font-size: $font-size-sm;
      color: $text-muted;
      margin-bottom: $spacing-sm;
      text-transform: uppercase;
      font-weight: $font-weight-semibold;
    }

    .stat-item {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: $spacing-xs 0;
      border-bottom: 1px solid $border-light;

      .stat-label {
        font-size: $font-size-sm;
        color: $text-muted;
      }

      .stat-value {
        font-weight: $font-weight-semibold;
        color: $text-color;

        &.text-danger {
          color: $danger-color;
        }
      }
    }
  }

  .action-buttons {
    margin-top: $spacing-lg;
  }
}

.map-container {
  flex: 1;
  position: relative;
  background: $gray-200;
}

.notification-panel {
  width: $notification-panel-width;
  background: white;
  border-left: 1px solid $border-color;
}

.loading-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(255, 255, 255, 0.9);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: $z-index-modal;

  .loading-content {
    text-align: center;

    .spinner {
      width: 40px;
      height: 40px;
      border: 3px solid $gray-300;
      border-top: 3px solid $primary-color;
      border-radius: 50%;
      animation: spin 1s linear infinite;
      margin: 0 auto $spacing-sm;
    }

    p {
      color: $text-color;
      font-weight: $font-weight-medium;
    }
  }
}

.error-toast {
  position: fixed;
  top: $spacing-lg;
  right: $spacing-lg;
  background: $danger-color;
  color: white;
  padding: $spacing-sm $spacing-md;
  border-radius: $border-radius;
  box-shadow: $shadow-lg;
  z-index: $z-index-toast;
  max-width: 400px;

  .error-content {
    display: flex;
    align-items: center;
    gap: $spacing-xs;

    .close-btn {
      background: none;
      border: none;
      color: white;
      cursor: pointer;
      padding: $spacing-xxs;
      margin-left: auto;
      border-radius: $border-radius-sm;
      transition: background-color $transition-fast;

      &:hover {
        background-color: rgba(255, 255, 255, 0.2);
      }
    }
  }
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

@keyframes pulse {
  0% { opacity: 1; }
  50% { opacity: 0.5; }
  100% { opacity: 1; }
}

// Responsive design
@media (max-width: $breakpoint-lg) {
  .sidebar {
    position: absolute;
    top: $header-height;
    left: 0;
    bottom: 0;
    z-index: $z-index-modal;
    transform: translateX(-100%);
    transition: transform 0.3s ease;

    &:not(.sidebar-collapsed) {
      transform: translateX(0);
    }

    &.sidebar-collapsed {
      width: $sidebar-collapsed-width;
      transform: translateX(0);
    }
  }

  .notification-panel {
    position: absolute;
    top: $header-height;
    right: 0;
    bottom: 0;
    z-index: $z-index-modal;
    transform: translateX(100%);
    transition: transform 0.3s ease;
  }
}

@media (max-width: $breakpoint-md) {
  .app-header .header-content {
    padding: $spacing-sm;

    .logo-section .app-title {
      font-size: $font-size-lg;
    }

    .status-section {
      flex-direction: column;
      gap: $spacing-xs;
      align-items: flex-end;

      .connection-status {
        font-size: $font-size-xs;
      }
    }
  }
}
</style>