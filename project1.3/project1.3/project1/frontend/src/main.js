import { createApp } from 'vue'
import { createPinia } from 'pinia'
import naive from 'naive-ui'
import router from './router'
import App from './App.vue'
import './styles/global.css'

const HEALTH_URL = '/api/health'
const POLL_INTERVAL_MS = 500
const REQUEST_TIMEOUT_MS = 3000
const SLOW_HINT_MS = 30000

async function isBackendReady() {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS)
  try {
    const res = await fetch(HEALTH_URL, {
      cache: 'no-store',
      signal: controller.signal,
    })
    await res.text()
    return res.ok
  } catch (e) {
    return false
  } finally {
    clearTimeout(timer)
  }
}

function showSlowHint() {
  const hint = document.querySelector('#boot-splash .text')
  if (hint) hint.textContent = '后端服务启动较慢，仍在等待，请稍候…'
}

async function waitForBackend() {
  const hintAt = Date.now() + SLOW_HINT_MS
  let hinted = false
  while (true) {
    if (await isBackendReady()) return
    if (!hinted && Date.now() >= hintAt) {
      hinted = true
      showSlowHint()
    }
    await new Promise((resolve) => setTimeout(resolve, POLL_INTERVAL_MS))
  }
}

await waitForBackend()

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.use(naive)
app.mount('#app')
