<template>
  <div class="layer-control">
    <div class="control-section">
      <h4>Map Layers</h4>

      <!-- Cattle Layer -->
      <div class="layer-item">
        <label class="checkbox-container">
          <input
            type="checkbox"
            :checked="localLayersVisible.cattle"
            @change="toggleLayer('cattle', $event.target.checked)"
          />
          <span class="checkmark"></span>
          <span class="layer-label">Show Cattle</span>
        </label>
        <div class="layer-count" v-if="cattleCount > 0">
          {{ cattleCount }} animals
        </div>
      </div>

      <!-- Resources Section -->
      <div class="subsection">
        <h5>Resources</h5>

        <div class="layer-item">
          <label class="checkbox-container">
            <input
              type="checkbox"
              :checked="localLayersVisible.waterResources"
              @change="toggleLayer('waterResources', $event.target.checked)"
            />
            <span class="checkmark"></span>
            <span class="layer-label water">💧 Water Troughs</span>
          </label>
          <div class="layer-count" v-if="waterResourceCount > 0">
            {{ waterResourceCount }}
          </div>
        </div>

        <div class="layer-item">
          <label class="checkbox-container">
            <input
              type="checkbox"
              :checked="localLayersVisible.feedResources"
              @change="toggleLayer('feedResources', $event.target.checked)"
            />
            <span class="checkmark"></span>
            <span class="layer-label feed">🌾 Feeding Stations</span>
          </label>
          <div class="layer-count" v-if="feedResourceCount > 0">
            {{ feedResourceCount }}
          </div>
        </div>

        <div class="layer-item">
          <label class="checkbox-container">
            <input
              type="checkbox"
              :checked="localLayersVisible.shelterResources"
              @change="toggleLayer('shelterResources', $event.target.checked)"
            />
            <span class="checkmark"></span>
            <span class="layer-label shelter">🏠 Shelters</span>
          </label>
          <div class="layer-count" v-if="shelterResourceCount > 0">
            {{ shelterResourceCount }}
          </div>
        </div>
      </div>

      <!-- Geofence Layer -->
      <div class="layer-item">
        <label class="checkbox-container">
          <input
            type="checkbox"
            :checked="localLayersVisible.geofences"
            @change="toggleLayer('geofences', $event.target.checked)"
          />
          <span class="checkmark"></span>
          <span class="layer-label geofence">📍 Geofences</span>
        </label>
        <div class="layer-count" v-if="geofenceCount > 0">
          {{ geofenceCount }}
        </div>
      </div>

      <!-- Heatmap Toggle -->
      <div class="layer-item">
        <label class="checkbox-container">
          <input
            type="checkbox"
            :checked="localLayersVisible.heatmap"
            @change="toggleLayer('heatmap', $event.target.checked)"
          />
          <span class="checkmark"></span>
          <span class="layer-label heatmap">🔥 Heatmap</span>
        </label>
        <div class="heatmap-controls" v-if="localLayersVisible.heatmap">
          <label class="time-range">
            Time Range:
            <select
              v-model="heatmapHours"
              @change="updateHeatmapHours"
              class="time-select"
            >
              <option value="1">Last Hour</option>
              <option value="6">Last 6 Hours</option>
              <option value="24">Last 24 Hours</option>
              <option value="168">Last Week</option>
            </select>
          </label>
        </div>
      </div>
    </div>

    <!-- Quick Actions -->
    <div class="control-section">
      <h4>Quick Actions</h4>

      <button
        class="action-btn"
        @click="toggleAllLayers"
        :disabled="loading"
      >
        <i class="fas" :class="allLayersVisible ? 'fa-eye-slash' : 'fa-eye'"></i>
        {{ allLayersVisible ? 'Hide All' : 'Show All' }}
      </button>

      <button
        class="action-btn"
        @click="resetLayers"
        :disabled="loading"
      >
        <i class="fas fa-undo"></i>
        Reset to Default
      </button>

      <button
        class="action-btn"
        @click="refreshMapData"
        :disabled="loading"
      >
        <i class="fas" :class="loading ? 'fa-spinner fa-spin' : 'fa-sync-alt'"></i>
        {{ loading ? 'Refreshing...' : 'Refresh Map' }}
      </button>
    </div>

    <!-- Statistics -->
    <div class="control-section">
      <h4>Statistics</h4>

      <div class="stats-grid">
        <div class="stat-item">
          <div class="stat-label">Total Cattle</div>
          <div class="stat-value">{{ cattleCount }}</div>
        </div>
        <div class="stat-item">
          <div class="stat-label">Violations</div>
          <div class="stat-value" :class="{ 'text-danger': violationCount > 0 }">
            {{ violationCount }}
          </div>
        </div>
        <div class="stat-item">
          <div class="stat-label">Resources</div>
          <div class="stat-value">{{ totalResourceCount }}</div>
        </div>
        <div class="stat-item">
          <div class="stat-label">Active Areas</div>
          <div class="stat-value">{{ geofenceCount }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, watch } from 'vue'

export default {
  name: 'LayerControl',
  props: {
    layersVisible: {
      type: Object,
      required: true
    },
    cattleCount: {
      type: Number,
      default: 0
    },
    waterResourceCount: {
      type: Number,
      default: 0
    },
    feedResourceCount: {
      type: Number,
      default: 0
    },
    shelterResourceCount: {
      type: Number,
      default: 0
    },
    geofenceCount: {
      type: Number,
      default: 0
    },
    violationCount: {
      type: Number,
      default: 0
    },
    loading: {
      type: Boolean,
      default: false
    }
  },

  emits: [
    'layer-toggle',
    'heatmap-hours-change',
    'refresh-data'
  ],

  setup(props, { emit }) {
    // Local state for layers
    const localLayersVisible = ref({ ...props.layersVisible })
    const heatmapHours = ref(24)

    // Computed properties
    const totalResourceCount = computed(() =>
      props.waterResourceCount + props.feedResourceCount + props.shelterResourceCount
    )

    const allLayersVisible = computed(() => {
      const layers = ['cattle', 'waterResources', 'feedResources', 'shelterResources', 'geofences']
      return layers.every(layer => localLayersVisible.value[layer])
    })

    // Methods
    const toggleLayer = (layerName, isVisible) => {
      localLayersVisible.value[layerName] = isVisible
      emit('layer-toggle', layerName, isVisible)
    }

    const toggleAllLayers = () => {
      const newValue = !allLayersVisible.value
      const layers = ['cattle', 'waterResources', 'feedResources', 'shelterResources', 'geofences']

      layers.forEach(layer => {
        localLayersVisible.value[layer] = newValue
        emit('layer-toggle', layer, newValue)
      })
    }

    const resetLayers = () => {
      const defaultLayers = {
        cattle: true,
        waterResources: true,
        feedResources: true,
        shelterResources: true,
        geofences: true,
        heatmap: false
      }

      Object.keys(defaultLayers).forEach(layer => {
        localLayersVisible.value[layer] = defaultLayers[layer]
        emit('layer-toggle', layer, defaultLayers[layer])
      })

      heatmapHours.value = 24
      emit('heatmap-hours-change', 24)
    }

    const refreshMapData = () => {
      emit('refresh-data')
    }

    const updateHeatmapHours = () => {
      emit('heatmap-hours-change', parseInt(heatmapHours.value))
    }

    // Watch for prop changes
    watch(() => props.layersVisible, (newLayers) => {
      localLayersVisible.value = { ...newLayers }
    }, { deep: true })

    return {
      localLayersVisible,
      heatmapHours,
      totalResourceCount,
      allLayersVisible,
      toggleLayer,
      toggleAllLayers,
      resetLayers,
      refreshMapData,
      updateHeatmapHours
    }
  }
}
</script>

<style lang="scss" scoped>
.layer-control {
  background: white;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 16px;

  .control-section {
    margin-bottom: 20px;

    &:last-child {
      margin-bottom: 0;
    }

    h4 {
      margin: 0 0 12px 0;
      font-size: 14px;
      font-weight: 600;
      color: #333;
      border-bottom: 1px solid #eee;
      padding-bottom: 8px;
    }

    h5 {
      margin: 12px 0 8px 0;
      font-size: 12px;
      font-weight: 500;
      color: #666;
      text-transform: uppercase;
    }
  }

  .layer-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 8px;
    padding: 4px 0;

    .checkbox-container {
      display: flex;
      align-items: center;
      cursor: pointer;
      flex: 1;
    }

    input[type="checkbox"] {
      display: none;
    }

    .checkmark {
      width: 16px;
      height: 16px;
      border: 2px solid #ddd;
      border-radius: 3px;
      margin-right: 8px;
      position: relative;
      transition: all 0.2s;

      &:after {
        content: '';
        position: absolute;
        display: none;
        left: 5px;
        top: 2px;
        width: 3px;
        height: 6px;
        border: solid white;
        border-width: 0 2px 2px 0;
        transform: rotate(45deg);
      }
    }

    input:checked ~ .checkmark {
      background-color: #007bff;
      border-color: #007bff;

      &:after {
        display: block;
      }
    }

    .layer-label {
      font-size: 13px;
      color: #555;
      flex: 1;

      &.water {
        color: #007bff;
      }

      &.feed {
        color: #fd7e14;
      }

      &.shelter {
        color: #6f42c1;
      }

      &.geofence {
        color: #28a745;
      }

      &.heatmap {
        color: #dc3545;
      }
    }

    .layer-count {
      font-size: 11px;
      color: #888;
      background: #f8f9fa;
      padding: 2px 6px;
      border-radius: 10px;
      min-width: 20px;
      text-align: center;
    }

    .heatmap-controls {
      margin-left: 24px;
      margin-top: 4px;

      .time-range {
        display: flex;
        align-items: center;
        font-size: 11px;
        color: #666;
        gap: 4px;

        .time-select {
          font-size: 11px;
          padding: 2px 4px;
          border: 1px solid #ddd;
          border-radius: 3px;
          background: white;
        }
      }
    }
  }

  .subsection {
    margin: 12px 0;
    padding-left: 8px;
    border-left: 3px solid #f8f9fa;
  }

  .action-btn {
    width: 100%;
    padding: 8px 12px;
    margin-bottom: 8px;
    border: 1px solid #ddd;
    border-radius: 4px;
    background: white;
    color: #333;
    font-size: 12px;
    cursor: pointer;
    transition: all 0.2s;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 6px;

    &:hover:not(:disabled) {
      background: #f8f9fa;
      border-color: #007bff;
      color: #007bff;
    }

    &:disabled {
      opacity: 0.6;
      cursor: not-allowed;
    }

    &:last-child {
      margin-bottom: 0;
    }

    i {
      font-size: 11px;
    }
  }

  .stats-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;

    .stat-item {
      text-align: center;
      padding: 8px;
      background: #f8f9fa;
      border-radius: 4px;

      .stat-label {
        font-size: 10px;
        color: #666;
        margin-bottom: 2px;
      }

      .stat-value {
        font-size: 16px;
        font-weight: 600;
        color: #333;

        &.text-danger {
          color: #dc3545;
        }
      }
    }
  }
}

// Hover effects
.checkbox-container:hover .checkmark {
  border-color: #007bff;
}

.checkbox-container:hover .layer-label {
  color: #333;
}
</style>