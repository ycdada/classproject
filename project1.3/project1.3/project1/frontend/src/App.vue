<template>
  <n-config-provider :locale="zhCN" :theme-overrides="themeOverrides">
    <n-message-provider>
      <div class="app-shell">
        <header class="app-header">
          <router-link to="/dashboard" class="brand">
            <i class="brand-mark" aria-hidden="true"></i>
            <span class="brand-name">数据结构 · 智能出卷</span>
          </router-link>

          <nav class="top-nav" aria-label="主导航">
            <router-link
              v-for="node in navNodes" :key="node.path"
              :to="node.path" class="nav-item" :class="{ active: isActive(node) }"
            >
              {{ node.label }}
            </router-link>
          </nav>
        </header>

        <main class="app-main">
          <router-view />
        </main>
      </div>
    </n-message-provider>
  </n-config-provider>
</template>

<script setup>
import { zhCN } from 'naive-ui'
import { useRoute } from 'vue-router'

const route = useRoute()

const navNodes = [
  { label: '首页', path: '/dashboard', match: (p) => p === '/' || p.startsWith('/dashboard') },
  { label: '材料', path: '/materials/upload', match: (p) => p.startsWith('/materials') },
  { label: '知识树', path: '/knowledge', match: (p) => p.startsWith('/knowledge') },
  { label: '题库', path: '/questions', match: (p) => p.startsWith('/questions') },
  { label: '组卷', path: '/exams/create', match: (p) => p === '/exams/create' },
  { label: '试卷', path: '/exams', match: (p) => p.startsWith('/exams') && p !== '/exams/create' },
]

const isActive = (node) => node.match(route.path)

const themeOverrides = {
  common: {
    primaryColor: '#0E7C86',
    primaryColorHover: '#12939F',
    primaryColorPressed: '#0A6A73',
    primaryColorSuppl: '#0E7C86',
    errorColor: '#D14343',
    errorColorHover: '#DA5F5F',
    warningColor: '#B9760F',
    textColorBase: '#1A1D21',
    borderRadius: '8px',
    fontWeightStrong: '600',
  },
  Card: {
    borderColor: '#E8EAED',
    titleTextColor: '#1A1D21',
    titleFontSizeSmall: '14px',
  },
  DataTable: {
    thColor: '#FAFBFC',
    thTextColor: '#5F6672',
    borderColor: '#F1F2F4',
    thFontWeight: '600',
  },
  Tag: {
    borderRadius: '10px',
  },
}
</script>

<style scoped>
.app-shell {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.app-header {
  height: 60px;
  padding: 0 40px;
  background: #fff;
  border-bottom: 1px solid var(--line);
  display: flex;
  align-items: center;
  gap: 48px;
  position: sticky;
  top: 0;
  z-index: 100;
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  text-decoration: none;
  flex-shrink: 0;
}

.brand-mark {
  width: 22px;
  height: 22px;
  border-radius: 6px;
  background: var(--accent);
}

.brand-name {
  color: var(--ink);
  font-size: 15px;
  font-weight: 700;
  letter-spacing: 0.5px;
}

.top-nav {
  display: flex;
  gap: 6px;
  overflow-x: auto;
  scrollbar-width: none;
}

.top-nav::-webkit-scrollbar {
  display: none;
}

.nav-item {
  padding: 7px 14px;
  border-radius: 6px;
  color: var(--text-2);
  font-size: 14px;
  text-decoration: none;
  white-space: nowrap;
  transition: color 0.15s, background-color 0.15s;
}

.nav-item:hover {
  color: var(--ink);
  background: var(--line-soft);
}

.nav-item.active {
  color: var(--accent);
  background: var(--accent-bg);
  font-weight: 600;
}

.app-main {
  flex: 1;
  padding: 32px 24px;
}

@media (max-width: 768px) {
  .app-header {
    gap: 16px;
    padding: 0 12px;
  }

  .brand-name {
    display: none;
  }
}
</style>
