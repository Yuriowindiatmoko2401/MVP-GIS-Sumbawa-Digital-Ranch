<template>
  <div class="map-viewer">
    <div id="map" class="map-container"></div>

    <!-- Map Controls Overlay -->
    <div class="map-controls">
      <button
        class="control-btn"
        @click="zoomIn"
        title="Zoom In"
      >
        <i class="fas fa-plus"></i>
      </button>
      <button
        class="control-btn"
        @click="zoomOut"
        title="Zoom Out"
      >
        <i class="fas fa-minus"></i>
      </button>
      <button
        class="control-btn"
        @click="resetView"
        title="Reset View"
      >
        <i class="fas fa-home"></i>
      </button>
      <button
        class="control-btn"
        @click="toggleFullscreen"
        title="Toggle Fullscreen"
      >
        <i class="fas fa-expand"></i>
      </button>
    </div>

    <!-- Legend -->
    <div class="map-legend" v-if="showLegend">
      <h4>Legend</h4>
      <div class="legend-item">
        <div class="legend-marker healthy-cattle"></div>
        <span>Healthy Cattle</span>
      </div>
      <div class="legend-item">
        <div class="legend-marker warning-cattle"></div>
        <span>Needs Attention</span>
      </div>
      <div class="legend-item">
        <div class="legend-marker sick-cattle"></div>
        <span>Sick Cattle</span>
      </div>
      <div class="legend-item">
        <div class="legend-marker violation-cattle"></div>
        <span>Violation</span>
      </div>
      <div class="legend-item">
        <div class="legend-marker water-resource"></div>
        <span>Water Trough</span>
      </div>
      <div class="legend-item">
        <div class="legend-marker feed-resource"></div>
        <span>Feeding Station</span>
      </div>
      <div class="legend-item">
        <div class="legend-marker shelter-resource"></div>
        <span>Shelter</span>
      </div>
    </div>

    <!-- Loading Overlay -->
    <div v-if="loading" class="loading-overlay">
      <div class="loading-spinner"></div>
      <p>Loading map...</p>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

// Fix Leaflet default icon issue with Vite
delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: '/assets/leaflet/images/marker-icon-2x.png',
  iconUrl: '/assets/leaflet/images/marker-icon.png',
  shadowUrl: '/assets/leaflet/images/marker-shadow.png',
})

export default {
  name: 'MapViewer',
  props: {
    layersVisible: {
      type: Object,
      default: () => ({
        cattle: true,
        waterResources: true,
        feedResources: true,
        shelterResources: true,
        geofences: true,
        heatmap: false
      })
    },
    showHeatmap: {
      type: Boolean,
      default: false
    },
    cattleData: {
      type: Array,
      default: () => []
    },
    resourceData: {
      type: Array,
      default: () => []
    },
    geofenceData: {
      type: Array,
      default: () => []
    }
  },

  emits: [
    'map-ready',
    'cattle-click',
    'resource-click',
    'geofence-click',
    'map-click'
  ],

  setup(props, { emit }) {
    // Map instance and state
    const map = ref(null)
    const isMapReady = ref(false)
    const loading = ref(true)
    const showLegend = ref(true)

    // Layer groups
    const layers = ref({
      cattle: null,
      resources: null,
      geofences: null,
      heatmap: null
    })

    // Base map layer
    const baseLayer = ref(null)

    // Map center (Sumbawa coordinates)
    const defaultCenter = [-8.657382, 117.515206]
    const defaultZoom = 14

    // Initialize map
    const initializeMap = async () => {
      try {
        // Create map instance
        map.value = L.map('map', {
          center: defaultCenter,
          zoom: defaultZoom,
          zoomControl: false // We'll add custom controls
        })

        // Add tile layer (OpenStreetMap)
        baseLayer.value = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
          attribution: '© OpenStreetMap contributors',
          maxZoom: 19
        })
        baseLayer.value.addTo(map.value)

        // Initialize layer groups
        layers.value.cattle = L.layerGroup().addTo(map.value)
        layers.value.resources = L.layerGroup().addTo(map.value)
        layers.value.geofences = L.layerGroup().addTo(map.value)

        // Add event listeners
        map.value.on('click', handleMapClick)

        // Emit map ready event
        isMapReady.value = true
        loading.value = false
        emit('map-ready', map.value)

      } catch (error) {
        console.error('Failed to initialize map:', error)
        loading.value = false
      }
    }

    // Create custom icons
    const createCattleIcon = (healthStatus, geofenceStatus) => {
      const color = getMarkerColor(healthStatus, geofenceStatus)
      return L.divIcon({
        className: 'custom-marker',
        html: `<div style="background-color: ${color}; width: 20px; height: 20px; border-radius: 50%; border: 2px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3);"></div>`,
        iconSize: [20, 20],
        iconAnchor: [10, 10]
      })
    }

    const createResourceIcon = (resourceType) => {
      const iconConfig = getResourceIconConfig(resourceType)
      return L.divIcon({
        className: 'resource-marker',
        html: `<div style="background-color: ${iconConfig.color}; width: 16px; height: 16px; border-radius: 50%; border: 2px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3); display: flex; align-items: center; justify-content: center; font-size: 10px; color: white;">${iconConfig.symbol}</div>`,
        iconSize: [16, 16],
        iconAnchor: [8, 8]
      })
    }

    const getMarkerColor = (healthStatus, geofenceStatus) => {
      if (geofenceStatus === 'outside') return '#dc3545' // Red for violations
      switch (healthStatus) {
        case 'Sehat': return '#28a745' // Green
        case 'Perlu Perhatian': return '#ffc107' // Yellow
        case 'Sakit': return '#dc3545' // Red
        default: return '#6c757d' // Gray
      }
    }

    const getResourceIconConfig = (resourceType) => {
      switch (resourceType) {
        case 'water_trough': return { color: '#007bff', symbol: '💧' }
        case 'feeding_station': return { color: '#fd7e14', symbol: '🌾' }
        case 'shelter': return { color: '#6f42c1', symbol: '🏠' }
        default: return { color: '#6c757d', symbol: '📍' }
      }
    }

    // Update cattle markers
    const updateCattleMarkers = () => {
      if (!layers.value.cattle || !props.layersVisible.cattle) return

      // Clear existing markers
      layers.value.cattle.clearLayers()

      // Add new markers
      props.cattleData.forEach(cattle => {
        if (cattle.location) {
          const marker = L.marker(
            [cattle.location.lat, cattle.location.lng],
            {
              icon: createCattleIcon(cattle.healthStatus, cattle.geofenceStatus),
              title: cattle.identifier
            }
          )

          // Create popup content
          const popupContent = `
            <div class="cattle-popup">
              <h4>${cattle.identifier}</h4>
              <p><strong>Age:</strong> ${cattle.age} years</p>
              <p><strong>Health:</strong> ${cattle.healthStatus}</p>
              <p><strong>Status:</strong> ${cattle.geofenceStatus}</p>
              <p><strong>Last Update:</strong> ${new Date(cattle.lastUpdate).toLocaleString()}</p>
            </div>
          `

          marker.bindPopup(popupContent)
          marker.on('click', () => emit('cattle-click', cattle))
          marker.addTo(layers.value.cattle)
        }
      })
    }

    // Update resource markers
    const updateResourceMarkers = () => {
      if (!layers.value.resources) return

      // Clear existing markers
      layers.value.resources.clearLayers()

      // Add new markers
      props.resourceData.forEach(resource => {
        if (resource.location && (
          (resource.type === 'water_trough' && props.layersVisible.waterResources) ||
          (resource.type === 'feeding_station' && props.layersVisible.feedResources) ||
          (resource.type === 'shelter' && props.layersVisible.shelterResources)
        )) {
          const marker = L.marker(
            [resource.location.lat, resource.location.lng],
            {
              icon: createResourceIcon(resource.type),
              title: resource.name
            }
          )

          // Create popup content
          const popupContent = `
            <div class="resource-popup">
              <h4>${resource.name}</h4>
              <p><strong>Type:</strong> ${resource.type.replace('_', ' ')}</p>
              <p><strong>Capacity:</strong> ${resource.capacity || 'N/A'}</p>
              <p><strong>Current Usage:</strong> ${resource.currentUsage || 0}</p>
            </div>
          `

          marker.bindPopup(popupContent)
          marker.on('click', () => emit('resource-click', resource))
          marker.addTo(layers.value.resources)
        }
      })
    }

    // Update geofence polygons
    const updateGeofenceLayers = () => {
      if (!layers.value.geofences || !props.layersVisible.geofences) return

      // Clear existing layers
      layers.value.geofences.clearLayers()

      // Add new polygons
      props.geofenceData.forEach(geofence => {
        if (geofence.boundary && geofence.boundary.coordinates) {
          // Convert GeoJSON coordinates to Leaflet format
          const coordinates = geofence.boundary.coordinates[0].map(coord => [coord[1], coord[0]])

          const polygon = L.polygon(coordinates, {
            color: '#28a745',
            fillColor: '#28a745',
            fillOpacity: 0.1,
            weight: 2
          })

          // Create popup content
          const popupContent = `
            <div class="geofence-popup">
              <h4>${geofence.name}</h4>
              <p><strong>Cattle Count:</strong> ${geofence.cattleCount || 0}</p>
              <p><strong>Created:</strong> ${new Date(geofence.createdAt).toLocaleDateString()}</p>
            </div>
          `

          polygon.bindPopup(popupContent)
          polygon.on('click', () => emit('geofence-click', geofence))
          polygon.addTo(layers.value.geofences)
        }
      })
    }

    // Map control functions
    const zoomIn = () => {
      if (map.value) map.value.zoomIn()
    }

    const zoomOut = () => {
      if (map.value) map.value.zoomOut()
    }

    const resetView = () => {
      if (map.value) {
        map.value.setView(defaultCenter, defaultZoom)
      }
    }

    const toggleFullscreen = () => {
      const mapElement = document.getElementById('map')
      if (!document.fullscreenElement) {
        mapElement.requestFullscreen()
      } else {
        document.exitFullscreen()
      }
    }

    const handleMapClick = (e) => {
      emit('map-click', {
        lat: e.latlng.lat,
        lng: e.latlng.lng
      })
    }

    const refreshLayers = () => {
      updateCattleMarkers()
      updateResourceMarkers()
      updateGeofenceLayers()
    }

    // Watch for data changes
    watch(() => props.cattleData, updateCattleMarkers, { deep: true })
    watch(() => props.resourceData, updateResourceMarkers, { deep: true })
    watch(() => props.geofenceData, updateGeofenceLayers, { deep: true })
    watch(() => props.layersVisible, refreshLayers, { deep: true })

    // Lifecycle hooks
    onMounted(async () => {
      await nextTick()
      await initializeMap()
    })

    onUnmounted(() => {
      if (map.value) {
        map.value.remove()
        map.value = null
      }
    })

    return {
      map,
      isMapReady,
      loading,
      showLegend,
      zoomIn,
      zoomOut,
      resetView,
      toggleFullscreen,
      refreshLayers
    }
  }
}
</script>

<style lang="scss" scoped>
.map-viewer {
  position: relative;
  width: 100%;
  height: 100%;
}

.map-container {
  width: 100%;
  height: 100%;
  min-height: 400px;
}

.map-controls {
  position: absolute;
  top: 10px;
  right: 10px;
  z-index: 1000;
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.control-btn {
  background: white;
  border: 1px solid #ccc;
  border-radius: 4px;
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  transition: all 0.2s;

  &:hover {
    background: #f8f9fa;
    border-color: #007bff;
  }

  i {
    font-size: 14px;
    color: #495057;
  }
}

.map-legend {
  position: absolute;
  bottom: 10px;
  left: 10px;
  background: rgba(255, 255, 255, 0.95);
  border: 1px solid #ccc;
  border-radius: 4px;
  padding: 10px;
  z-index: 1000;
  min-width: 150px;

  h4 {
    margin: 0 0 8px 0;
    font-size: 12px;
    font-weight: bold;
    color: #333;
  }
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;

  span {
    font-size: 11px;
    color: #666;
  }
}

.legend-marker {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  border: 1px solid #fff;
  box-shadow: 0 1px 2px rgba(0,0,0,0.2);

  &.healthy-cattle {
    background-color: #28a745;
  }

  &.warning-cattle {
    background-color: #ffc107;
  }

  &.sick-cattle {
    background-color: #dc3545;
  }

  &.violation-cattle {
    background-color: #dc3545;
    border: 2px solid #721c24;
  }

  &.water-resource {
    background-color: #007bff;
  }

  &.feed-resource {
    background-color: #fd7e14;
  }

  &.shelter-resource {
    background-color: #6f42c1;
  }
}

.loading-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(255, 255, 255, 0.9);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  z-index: 2000;

  p {
    margin-top: 10px;
    font-size: 14px;
    color: #666;
  }
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #007bff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

// Global styles for popups
:global(.cattle-popup),
:global(.resource-popup),
:global(.geofence-popup) {
  min-width: 200px;

  h4 {
    margin: 0 0 8px 0;
    font-size: 14px;
    font-weight: bold;
    color: #333;
  }

  p {
    margin: 4px 0;
    font-size: 12px;
    color: #666;
  }

  strong {
    color: #333;
  }
}
</style>