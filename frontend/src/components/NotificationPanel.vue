<template>
  <div class="notification-panel">
    <div class="panel-header">
      <h3>
        <i class="fas fa-bell"></i>
        Notifications
        <span v-if="unreadCount > 0" class="notification-badge">
          {{ unreadCount }}
        </span>
      </h3>
      <div class="panel-controls">
        <button
          class="control-btn"
          @click="toggleAutoScroll"
          :title="autoScroll ? 'Disable Auto Scroll' : 'Enable Auto Scroll'"
          :class="{ active: autoScroll }"
        >
          <i class="fas" :class="autoScroll ? 'fa-arrow-down' : 'fa-pause'"></i>
        </button>
        <button
          class="control-btn"
          @click="toggleSound"
          :title="soundEnabled ? 'Mute Notifications' : 'Unmute Notifications'"
          :class="{ active: soundEnabled }"
        >
          <i class="fas" :class="soundEnabled ? 'fa-volume-up' : 'fa-volume-mute'"></i>
        </button>
        <button
          class="control-btn"
          @click="markAllAsRead"
          title="Mark All as Read"
          :disabled="notifications.length === 0"
        >
          <i class="fas fa-check-double"></i>
        </button>
        <button
          class="control-btn"
          @click="clearAll"
          title="Clear All"
          :disabled="notifications.length === 0"
        >
          <i class="fas fa-trash"></i>
        </button>
      </div>
    </div>

    <!-- Filter Tabs -->
    <div class="filter-tabs">
      <button
        class="tab-btn"
        :class="{ active: activeFilter === 'all' }"
        @click="setActiveFilter('all')"
      >
        All ({{ notifications.length }})
      </button>
      <button
        class="tab-btn"
        :class="{ active: activeFilter === 'unread' }"
        @click="setActiveFilter('unread')"
      >
        Unread ({{ unreadCount }})
      </button>
      <button
        class="tab-btn"
        :class="{ active: activeFilter === 'violations' }"
        @click="setActiveFilter('violations')"
      >
        Violations ({{ violationCount }})
      </button>
      <button
        class="tab-btn"
        :class="{ active: activeFilter === 'system' }"
        @click="setActiveFilter('system')"
      >
        System
      </button>
    </div>

    <!-- Notifications List -->
    <div class="notifications-list" ref="notificationsList">
      <div
        v-for="notification in filteredNotifications"
        :key="notification.id"
        class="notification-item"
        :class="[
          `notification-${notification.type}`,
          { 'notification-unread': !notification.read, 'notification-high': notification.priority === 'high' }
        ]"
        @click="handleNotificationClick(notification)"
      >
        <!-- Notification Icon -->
        <div class="notification-icon">
          <i :class="getNotificationIcon(notification.type)"></i>
        </div>

        <!-- Notification Content -->
        <div class="notification-content">
          <div class="notification-header">
            <h4 class="notification-title">{{ notification.title }}</h4>
            <span class="notification-time">
              {{ formatNotificationTime(notification.timestamp) }}
            </span>
          </div>
          <p class="notification-message">{{ notification.message }}</p>

          <!-- Notification Actions -->
          <div v-if="notification.actions && notification.actions.length > 0" class="notification-actions">
            <button
              v-for="action in notification.actions"
              :key="action.label"
              class="action-btn"
              :class="action.style || 'primary'"
              @click.stop="handleActionClick(notification, action)"
            >
              {{ action.label }}
            </button>
          </div>

          <!-- Notification Details -->
          <div v-if="notification.expanded && notification.data" class="notification-details">
            <pre>{{ JSON.stringify(notification.data, null, 2) }}</pre>
          </div>
        </div>

        <!-- Notification Controls -->
        <div class="notification-controls">
          <button
            class="control-btn small"
            @click.stop="toggleRead(notification)"
            :title="notification.read ? 'Mark as Unread' : 'Mark as Read'"
          >
            <i class="fas" :class="notification.read ? 'fa-envelope' : 'fa-envelope-open'"></i>
          </button>
          <button
            class="control-btn small"
            @click.stop="removeNotification(notification.id)"
            title="Remove"
          >
            <i class="fas fa-times"></i>
          </button>
        </div>

        <!-- Unread Indicator -->
        <div v-if="!notification.read" class="unread-indicator"></div>
      </div>

      <!-- Empty State -->
      <div v-if="filteredNotifications.length === 0" class="empty-state">
        <i class="fas fa-bell-slash"></i>
        <p>No notifications</p>
        <small>{{ getEmptyStateMessage() }}</small>
      </div>
    </div>

    <!-- Quick Actions Footer -->
    <div class="panel-footer">
      <div class="quick-actions">
        <button
          class="quick-action-btn"
          @click="clearOldNotifications"
          title="Clear Old Notifications"
        >
          <i class="fas fa-history"></i>
          Clear Old
        </button>
        <button
          class="quick-action-btn"
          @click="exportNotifications"
          title="Export Notifications"
          :disabled="notifications.length === 0"
        >
          <i class="fas fa-download"></i>
          Export
        </button>
      </div>
      <div class="notification-stats">
        <small>{{ notificationStats }}</small>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, nextTick, watch, onMounted, onUnmounted } from 'vue'

export default {
  name: 'NotificationPanel',
  props: {
    notifications: {
      type: Array,
      required: true
    },
    maxHeight: {
      type: Number,
      default: 400
    }
  },

  emits: [
    'clear-notification',
    'clear-all-notifications',
    'mark-all-read',
    'notification-click',
    'action-click'
  ],

  setup(props, { emit }) {
    // Local state
    const notificationsList = ref(null)
    const autoScroll = ref(true)
    const soundEnabled = ref(true)
    const activeFilter = ref('all')

    // Computed properties
    const unreadCount = computed(() =>
      props.notifications.filter(n => !n.read).length
    )

    const violationCount = computed(() =>
      props.notifications.filter(n => n.type === 'violation').length
    )

    const filteredNotifications = computed(() => {
      switch (activeFilter.value) {
        case 'unread':
          return props.notifications.filter(n => !n.read)
        case 'violations':
          return props.notifications.filter(n => n.type === 'violation')
        case 'system':
          return props.notifications.filter(n => n.type === 'system')
        default:
          return props.notifications
      }
    })

    const notificationStats = computed(() => {
      const total = props.notifications.length
      const unread = unreadCount.value
      const violations = violationCount.value
      return `${total} total, ${unread} unread, ${violations} violations`
    })

    // Methods
    const getNotificationIcon = (type) => {
      const iconMap = {
        violation: 'fas fa-exclamation-triangle',
        warning: 'fas fa-exclamation-circle',
        error: 'fas fa-times-circle',
        success: 'fas fa-check-circle',
        info: 'fas fa-info-circle',
        system: 'fas fa-cog'
      }
      return iconMap[type] || 'fas fa-bell'
    }

    const formatNotificationTime = (timestamp) => {
      const date = new Date(timestamp)
      const now = new Date()
      const diffMs = now - date
      const diffMins = Math.floor(diffMs / 60000)
      const diffHours = Math.floor(diffMs / 3600000)
      const diffDays = Math.floor(diffMs / 86400000)

      if (diffMins < 1) return 'Just now'
      if (diffMins < 60) return `${diffMins}m ago`
      if (diffHours < 24) return `${diffHours}h ago`
      if (diffDays < 7) return `${diffDays}d ago`

      return date.toLocaleDateString()
    }

    const getEmptyStateMessage = () => {
      switch (activeFilter.value) {
        case 'unread': return 'No unread notifications'
        case 'violations': return 'No violation alerts'
        case 'system': return 'No system notifications'
        default: return 'All caught up!'
      }
    }

    const handleNotificationClick = (notification) => {
      // Toggle expanded state for showing details
      const index = props.notifications.findIndex(n => n.id === notification.id)
      if (index >= 0) {
        props.notifications[index].expanded = !props.notifications[index].expanded
      }

      emit('notification-click', notification)

      // Mark as read if it was unread
      if (!notification.read) {
        toggleRead(notification)
      }
    }

    const handleActionClick = (notification, action) => {
      emit('action-click', notification, action)
    }

    const toggleRead = (notification) => {
      emit('mark-read', notification.id)
    }

    const removeNotification = (notificationId) => {
      emit('clear-notification', notificationId)
    }

    const markAllAsRead = () => {
      emit('mark-all-read')
    }

    const clearAll = () => {
      if (props.notifications.length > 0 && confirm('Clear all notifications?')) {
        emit('clear-all-notifications')
      }
    }

    const clearOldNotifications = () => {
      const cutoffDate = new Date(Date.now() - 24 * 60 * 60 * 1000) // 24 hours ago
      const oldNotifications = props.notifications.filter(
        n => new Date(n.timestamp) < cutoffDate
      )

      if (oldNotifications.length > 0) {
        if (confirm(`Clear ${oldNotifications.length} old notifications?`)) {
          oldNotifications.forEach(n => removeNotification(n.id))
        }
      } else {
        alert('No old notifications to clear')
      }
    }

    const exportNotifications = () => {
      const dataStr = JSON.stringify(props.notifications, null, 2)
      const dataUri = 'data:application/json;charset=utf-8,' + encodeURIComponent(dataStr)

      const exportFileDefaultName = `notifications-${new Date().toISOString().split('T')[0]}.json`

      const linkElement = document.createElement('a')
      linkElement.setAttribute('href', dataUri)
      linkElement.setAttribute('download', exportFileDefaultName)
      linkElement.click()
    }

    const toggleAutoScroll = () => {
      autoScroll.value = !autoScroll.value
    }

    const toggleSound = () => {
      soundEnabled.value = !soundEnabled.value
    }

    const setActiveFilter = (filter) => {
      activeFilter.value = filter
    }

    const scrollToBottom = async () => {
      if (autoScroll.value && notificationsList.value) {
        await nextTick()
        notificationsList.value.scrollTop = notificationsList.value.scrollHeight
      }
    }

    // Watch for notifications changes and auto-scroll
    watch(() => props.notifications.length, scrollToBottom)

    // Watch for filter changes and scroll to top
    watch(activeFilter, () => {
      if (notificationsList.value) {
        notificationsList.value.scrollTop = 0
      }
    })

    // Lifecycle
    onMounted(() => {
      scrollToBottom()
    })

    return {
      notificationsList,
      autoScroll,
      soundEnabled,
      activeFilter,
      unreadCount,
      violationCount,
      filteredNotifications,
      notificationStats,
      getNotificationIcon,
      formatNotificationTime,
      getEmptyStateMessage,
      handleNotificationClick,
      handleActionClick,
      toggleRead,
      removeNotification,
      markAllAsRead,
      clearAll,
      clearOldNotifications,
      exportNotifications,
      toggleAutoScroll,
      toggleSound,
      setActiveFilter
    }
  }
}
</script>

<style lang="scss" scoped>
.notification-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: white;
  border-left: 1px solid #e0e0e0;
  max-width: 350px;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid #e0e0e0;
  background: #f8f9fa;

  h3 {
    margin: 0;
    font-size: 16px;
    font-weight: 600;
    color: #333;
    display: flex;
    align-items: center;
    gap: 8px;

    i {
      color: #007bff;
    }
  }

  .notification-badge {
    background: #dc3545;
    color: white;
    font-size: 10px;
    font-weight: bold;
    padding: 2px 6px;
    border-radius: 10px;
    min-width: 18px;
    text-align: center;
  }

  .panel-controls {
    display: flex;
    gap: 4px;

    .control-btn {
      background: transparent;
      border: 1px solid #ddd;
      border-radius: 4px;
      width: 28px;
      height: 28px;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      font-size: 12px;
      color: #666;
      transition: all 0.2s;

      &:hover:not(:disabled) {
        background: #e9ecef;
        border-color: #007bff;
        color: #007bff;
      }

      &.active {
        background: #007bff;
        border-color: #007bff;
        color: white;
      }

      &:disabled {
        opacity: 0.5;
        cursor: not-allowed;
      }

      &.small {
        width: 24px;
        height: 24px;
        font-size: 10px;
      }
    }
  }
}

.filter-tabs {
  display: flex;
  border-bottom: 1px solid #e0e0e0;
  background: white;

  .tab-btn {
    flex: 1;
    padding: 8px 12px;
    border: none;
    background: transparent;
    font-size: 11px;
    font-weight: 500;
    color: #666;
    cursor: pointer;
    border-bottom: 2px solid transparent;
    transition: all 0.2s;

    &:hover {
      background: #f8f9fa;
      color: #333;
    }

    &.active {
      color: #007bff;
      border-bottom-color: #007bff;
      background: #f8f9fa;
    }
  }
}

.notifications-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;

  &::-webkit-scrollbar {
    width: 6px;
  }

  &::-webkit-scrollbar-track {
    background: #f1f1f1;
  }

  &::-webkit-scrollbar-thumb {
    background: #c1c1c1;
    border-radius: 3px;

    &:hover {
      background: #a8a8a8;
    }
  }
}

.notification-item {
  position: relative;
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px;
  margin-bottom: 8px;
  background: white;
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    transform: translateY(-1px);
  }

  &.notification-unread {
    border-left: 4px solid #007bff;
    background: #f8f9ff;
  }

  &.notification-high {
    border-left-color: #dc3545;
  }

  &.notification-violation {
    border-left-color: #dc3545;
  }

  &.notification-warning {
    border-left-color: #ffc107;
  }

  &.notification-error {
    border-left-color: #dc3545;
  }

  &.notification-success {
    border-left-color: #28a745;
  }
}

.notification-icon {
  flex-shrink: 0;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  font-size: 10px;
  color: white;

  .notification-violation & {
    background: #dc3545;
  }

  .notification-warning & {
    background: #ffc107;
    color: #333;
  }

  .notification-error & {
    background: #dc3545;
  }

  .notification-success & {
    background: #28a745;
  }

  .notification-info &,
  .notification-system & {
    background: #007bff;
  }
}

.notification-content {
  flex: 1;
  min-width: 0;
}

.notification-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 4px;

  .notification-title {
    margin: 0;
    font-size: 13px;
    font-weight: 600;
    color: #333;
    line-height: 1.2;
  }

  .notification-time {
    font-size: 10px;
    color: #999;
    white-space: nowrap;
    margin-left: 8px;
  }
}

.notification-message {
  margin: 0;
  font-size: 12px;
  color: #666;
  line-height: 1.4;
}

.notification-actions {
  display: flex;
  gap: 6px;
  margin-top: 8px;

  .action-btn {
    padding: 4px 8px;
    font-size: 10px;
    border: 1px solid #ddd;
    border-radius: 3px;
    background: white;
    color: #666;
    cursor: pointer;
    transition: all 0.2s;

    &:hover {
      background: #f8f9fa;
      border-color: #007bff;
      color: #007bff;
    }

    &.primary {
      background: #007bff;
      border-color: #007bff;
      color: white;

      &:hover {
        background: #0056b3;
      }
    }

    &.secondary {
      background: #6c757d;
      border-color: #6c757d;
      color: white;

      &:hover {
        background: #545b62;
      }
    }
  }
}

.notification-details {
  margin-top: 8px;
  padding: 8px;
  background: #f8f9fa;
  border-radius: 4px;
  font-size: 10px;
  color: #666;

  pre {
    margin: 0;
    white-space: pre-wrap;
    word-break: break-word;
  }
}

.notification-controls {
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex-shrink: 0;
}

.unread-indicator {
  position: absolute;
  top: 8px;
  right: 8px;
  width: 8px;
  height: 8px;
  background: #007bff;
  border-radius: 50%;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  color: #999;
  text-align: center;

  i {
    font-size: 24px;
    margin-bottom: 12px;
    opacity: 0.5;
  }

  p {
    margin: 0 0 4px 0;
    font-size: 14px;
    font-weight: 500;
  }

  small {
    font-size: 12px;
    color: #bbb;
  }
}

.panel-footer {
  border-top: 1px solid #e0e0e0;
  padding: 8px 16px;
  background: #f8f9fa;
}

.quick-actions {
  display: flex;
  gap: 8px;
  margin-bottom: 8px;

  .quick-action-btn {
    flex: 1;
    padding: 6px 12px;
    border: 1px solid #ddd;
    border-radius: 4px;
    background: white;
    font-size: 11px;
    color: #666;
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
      opacity: 0.5;
      cursor: not-allowed;
    }

    i {
      font-size: 10px;
    }
  }
}

.notification-stats {
  text-align: center;

  small {
    font-size: 10px;
    color: #999;
  }
}

// Responsive design
@media (max-width: 768px) {
  .notification-panel {
    max-width: 100%;
  }

  .notification-header {
    .notification-title {
      font-size: 12px;
    }

    .notification-time {
      font-size: 9px;
    }
  }

  .notification-message {
    font-size: 11px;
  }
}
</style>