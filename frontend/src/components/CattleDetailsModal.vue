<template>
  <div class="modal-overlay" @click="handleClose">
    <div class="modal-content" @click.stop>
      <div class="modal-header">
        <h2>Cattle Details</h2>
        <button class="close-btn" @click="handleClose">
          <i class="fas fa-times"></i>
        </button>
      </div>

      <div class="modal-body" v-if="cattle">
        <div class="cattle-info">
          <div class="info-row">
            <label>Identifier:</label>
            <span>{{ cattle.identifier }}</span>
          </div>
          <div class="info-row">
            <label>Age:</label>
            <span>{{ cattle.age }} years</span>
          </div>
          <div class="info-row">
            <label>Health Status:</label>
            <span :class="`status-${cattle.healthStatus.toLowerCase().replace(' ', '-')}`">
              {{ cattle.healthStatus }}
            </span>
          </div>
          <div class="info-row">
            <label>Geofence Status:</label>
            <span :class="`status-${cattle.geofenceStatus}`">
              {{ cattle.geofenceStatus }}
            </span>
          </div>
          <div class="info-row">
            <label>Last Update:</label>
            <span>{{ formatDate(cattle.lastUpdate) }}</span>
          </div>
          <div class="info-row" v-if="cattle.location">
            <label>Location:</label>
            <span>{{ formatLocation(cattle.location) }}</span>
          </div>
        </div>
      </div>

      <div class="modal-footer">
        <button class="btn btn-secondary" @click="handleClose">Close</button>
        <button class="btn btn-primary" @click="viewHistory">View History</button>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'CattleDetailsModal',
  props: {
    cattle: {
      type: Object,
      required: true
    }
  },

  emits: ['close'],

  setup(props, { emit }) {
    const handleClose = () => {
      emit('close')
    }

    const formatDate = (dateString) => {
      return new Date(dateString).toLocaleString()
    }

    const formatLocation = (location) => {
      return `${location.lat.toFixed(6)}, ${location.lng.toFixed(6)}`
    }

    const viewHistory = () => {
      // Emit event to view cattle history
      console.log('View history for:', props.cattle.identifier)
    }

    return {
      handleClose,
      formatDate,
      formatLocation,
      viewHistory
    }
  }
}
</script>

<style lang="scss" scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
}

.modal-content {
  background: white;
  border-radius: 8px;
  width: 90%;
  max-width: 500px;
  max-height: 80vh;
  overflow: auto;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid #e0e0e0;

  h2 {
    margin: 0;
    font-size: 18px;
    font-weight: 600;
    color: #333;
  }

  .close-btn {
    background: transparent;
    border: none;
    font-size: 18px;
    color: #666;
    cursor: pointer;
    padding: 4px;
    border-radius: 4px;

    &:hover {
      background: #f8f9fa;
      color: #333;
    }
  }
}

.modal-body {
  padding: 20px;
}

.cattle-info {
  .info-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 0;
    border-bottom: 1px solid #f8f9fa;

    &:last-child {
      border-bottom: none;
    }

    label {
      font-weight: 500;
      color: #666;
      font-size: 14px;
    }

    span {
      font-size: 14px;
      color: #333;

      &.status-sehat {
        color: #28a745;
        font-weight: 500;
      }

      &.status-perlu-perhatian {
        color: #ffc107;
        font-weight: 500;
      }

      &.status-sakit {
        color: #dc3545;
        font-weight: 500;
      }

      &.status-within {
        color: #28a745;
        font-weight: 500;
      }

      &.status-outside {
        color: #dc3545;
        font-weight: 500;
      }
    }
  }
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 20px;
  border-top: 1px solid #e0e0e0;
}

.btn {
  padding: 8px 16px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;

  &.btn-primary {
    background: #007bff;
    border-color: #007bff;
    color: white;

    &:hover {
      background: #0056b3;
    }
  }

  &.btn-secondary {
    background: #6c757d;
    border-color: #6c757d;
    color: white;

    &:hover {
      background: #545b62;
    }
  }
}
</style>