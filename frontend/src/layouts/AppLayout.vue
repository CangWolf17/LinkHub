<template>
  <div class="flex h-screen overflow-hidden bg-gray-50">
    <!-- 左侧导航栏 -->
    <aside class="w-[var(--sidebar-width)] flex-shrink-0 bg-white border-r border-gray-200 flex flex-col">
      <!-- Logo -->
      <div class="h-[var(--header-height)] flex items-center px-5 border-b border-gray-200">
        <h1 class="text-lg font-bold text-blue-600 tracking-tight">LinkHub</h1>
      </div>

      <!-- 导航链接 -->
      <nav class="flex-1 py-4 px-3 space-y-1">
        <router-link
          v-for="item in navItems"
          :key="item.path"
          :to="item.path"
          class="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors"
          :class="[
            $route.path === item.path
              ? 'bg-blue-50 text-blue-700'
              : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900',
          ]"
        >
          <span class="text-base">{{ item.icon }}</span>
          <span>{{ item.label }}</span>
        </router-link>
      </nav>

      <!-- 底部状态 -->
      <div class="px-4 py-3 border-t border-gray-200">
        <div class="flex items-center gap-2 text-xs text-gray-400">
          <span
            class="w-2 h-2 rounded-full"
            :class="serverOnline ? 'bg-green-400' : 'bg-red-400'"
          />
          <span>{{ serverOnline ? 'Backend Online' : 'Backend Offline' }}</span>
        </div>
      </div>
    </aside>

    <!-- 右侧主体 -->
    <div class="flex-1 flex flex-col overflow-hidden">
      <!-- 顶部搜索栏 -->
      <header class="h-[var(--header-height)] flex-shrink-0 bg-white border-b border-gray-200 flex items-center px-6 gap-4">
        <SearchBar class="flex-1 max-w-xl" />

        <!-- LLM 状态 Badge -->
        <div
          class="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium cursor-pointer transition-colors"
          :class="llmBadgeClass"
          @click="llmMonitor.toggle()"
          title="LLM Debug Monitor"
        >
          <span class="w-1.5 h-1.5 rounded-full" :class="llmDotClass" />
          <span>LLM</span>
        </div>
      </header>

      <!-- 页面内容 -->
      <main class="flex-1 overflow-y-auto p-6">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </main>
    </div>

    <!-- LLM Debug 悬浮窗 -->
    <LlmDebugMonitor />

    <!-- 首次启动向导 -->
    <SetupWizard v-if="showWizard" @done="onWizardDone" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { getHealth, getLlmConfig, getInitStatus } from '@/api'
import { useLlmMonitor } from '@/composables/useLlmMonitor'
import SearchBar from '@/components/SearchBar.vue'
import LlmDebugMonitor from '@/components/LlmDebugMonitor.vue'
import SetupWizard from '@/components/SetupWizard.vue'

const { state: _llmState, ...llmMonitor } = useLlmMonitor()

const navItems = [
  { path: '/software', label: '软件舱', icon: '📦' },
  { path: '/workspaces', label: '工作区', icon: '📂' },
  { path: '/logs', label: '日志', icon: '📋' },
  { path: '/settings', label: '设置', icon: '⚙️' },
]

const serverOnline = ref(false)
const llmConfigured = ref(false)
const showWizard = ref(false)

const llmBadgeClass = computed(() =>
  llmConfigured.value
    ? 'bg-green-50 text-green-700 hover:bg-green-100'
    : 'bg-gray-100 text-gray-500 hover:bg-gray-200',
)

const llmDotClass = computed(() =>
  llmConfigured.value ? 'bg-green-500' : 'bg-gray-400',
)

async function checkStatus() {
  try {
    await getHealth()
    serverOnline.value = true
  } catch {
    serverOnline.value = false
  }

  try {
    const { data } = await getLlmConfig()
    llmConfigured.value = data.has_api_key
  } catch {
    llmConfigured.value = false
  }
}

async function checkInitStatus() {
  try {
    const { data } = await getInitStatus()
    if (data.needs_setup) {
      showWizard.value = true
    }
  } catch {
    // 无法判断时不弹窗，静默失败
  }
}

function onWizardDone() {
  showWizard.value = false
  checkStatus()
}

onMounted(() => {
  checkStatus()
  checkInitStatus()
  // 每 30 秒检查一次
  setInterval(checkStatus, 30_000)
})
</script>
