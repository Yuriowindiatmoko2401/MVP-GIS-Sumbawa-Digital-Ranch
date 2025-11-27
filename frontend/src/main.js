import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'

// Import styles
import './styles/main.scss'

// Create app instance
const app = createApp(App)

// Use Pinia for state management
app.use(createPinia())

// Global properties
app.config.globalProperties.$appName = 'Sumbawa Digital Ranch'
app.config.globalProperties.$version = '1.0.0'

// Error handler
app.config.errorHandler = (err, vm, info) => {
  console.error('Vue Error:', err)
  console.error('Component:', vm)
  console.error('Error Info:', info)

  // In production, you might want to send this to an error tracking service
  if (import.meta.env.PROD) {
    // error tracking service call here
  }
}

// Warning handler
app.config.warnHandler = (msg, vm, trace) => {
  console.warn('Vue Warning:', msg)
  console.warn('Component:', vm)
  console.warn('Trace:', trace)
}

// Mount app
app.mount('#app')

// Performance monitoring (development only)
if (!import.meta.env.PROD) {
  console.log('🚀 Sumbawa Digital Ranch - Development Mode')
  console.log('Vue Version:', app.version)
  console.log('Environment:', import.meta.env.MODE)

  // Optional: Enable Vue devtools performance timing
  if (typeof window !== 'undefined' && window.__VUE_DEVTOOLS_GLOBAL_HOOK__) {
    window.__VUE_DEVTOOLS_GLOBAL_HOOK__.on = true
  }
}