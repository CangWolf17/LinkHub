<template>
  <div class="flex h-screen overflow-hidden bg-gray-50">
    <!-- 左侧导航栏 -->
    <aside class="w-[var(--sidebar-width)] flex-shrink-0 bg-white border-r border-gray-200 flex flex-col">
      <!-- Logo -->
      <div class="h-[var(--header-height)] flex items-center px-5 border-b border-gray-200">
        <h1 class="text-lg font-bold text-blue-600 tracking-tight">LinkHub</h1>
      </div>

      <!-- 导航链接 -->
      <nav class="flex-1 py-4 px-3 space-y-1 overflow-y-auto">
        <template v-for="item in navItems" :key="item.path">
          <!-- 普通导航项 -->
          <router-link
            v-if="!item.children"
            :to="item.path"
            class="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors"
            :class="[
              isNavActive(item.path)
                ? 'bg-blue-50 text-blue-700'
                : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900',
            ]"
          >
            <component :is="item.icon" :size="18" class="flex-shrink-0" />
            <span>{{ item.label }}</span>
          </router-link>

          <!-- 可展开导航项（工作区） -->
          <div v-else>
            <button
              class="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors"
              :class="[
                isNavActive(item.path)
                  ? 'bg-blue-50 text-blue-700'
                  : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900',
              ]"
              @click="handleExpandableClick(item)"
            >
              <component :is="item.icon" :size="18" class="flex-shrink-0" />
              <span class="flex-1 text-left">{{ item.label }}</span>
              <ChevronDown
                v-if="item.children.length > 0"
                :size="14"
                class="transition-transform duration-200 text-gray-400"
                :class="expandedNav.has(item.path) ? '' : '-rotate-90'"
              />
            </button>
            <!-- 子菜单 -->
            <div v-if="expandedNav.has(item.path) && item.children.length > 0" class="ml-6 mt-0.5 space-y-0.5">
              <!-- 全部 -->
              <router-link
                :to="item.path"
                class="flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium transition-colors"
                :class="[
                  $route.path === item.path && !$route.query.dir
                    ? 'bg-blue-50 text-blue-600'
                    : 'text-gray-500 hover:bg-gray-50 hover:text-gray-700',
                ]"
              >
                <span class="w-1.5 h-1.5 rounded-full bg-gray-300" />
                全部
              </router-link>
              <!-- 各目录子项 -->
              <template v-for="child in item.children" :key="child.path">
                <!-- 重命名模式 -->
                <div v-if="renamingPath === child.path" class="flex items-center gap-2 px-3 py-1">
                  <span class="w-1.5 h-1.5 rounded-full" :class="child.dotColor" />
                  <input
                    v-model="renameInput"
                    class="flex-1 min-w-0 text-xs px-1.5 py-0.5 border border-blue-400 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
                    @keyup.enter="confirmRename(child.path)"
                    @keyup.escape="cancelRename"
                    @blur="confirmRename(child.path)"
                    @vue:mounted="($event: any) => $event.el.focus()"
                  />
                </div>
                <!-- 正常显示 -->
                <router-link
                  v-else
                  :to="{ path: item.path, query: { dir: child.path } }"
                  class="flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium transition-colors truncate"
                  :class="[
                    $route.path === item.path && $route.query.dir === child.path
                      ? 'bg-blue-50 text-blue-600'
                      : 'text-gray-500 hover:bg-gray-50 hover:text-gray-700',
                  ]"
                  :title="child.path"
                  @dblclick.prevent="startRename(child.path, child.label)"
                >
                  <span class="w-1.5 h-1.5 rounded-full" :class="child.dotColor" />
                  {{ child.label }}
                </router-link>
              </template>
            </div>
          </div>
        </template>
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
import { ref, onMounted, computed, type Component } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getHealth, getInitStatus, getAllowedDirs, updateAllowedDirs, llmHealthCheck } from '@/api'
import type { DirEntry } from '@/api'
import { useLlmMonitor } from '@/composables/useLlmMonitor'
import SearchBar from '@/components/SearchBar.vue'
import LlmDebugMonitor from '@/components/LlmDebugMonitor.vue'
import SetupWizard from '@/components/SetupWizard.vue'
import { Home, Package, FolderOpen, ClipboardList, Settings, ChevronDown } from 'lucide-vue-next'

const route = useRoute()
const router = useRouter()
const { state: _llmState, ...llmMonitor } = useLlmMonitor()

// 工作区白名单目录列表（用于侧边栏子菜单）
const workspaceDirEntries = ref<Array<{ path: string; label: string; dotColor: string }>>([])
const allDirEntries = ref<DirEntry[]>([])  // 完整列表（保存时用）
const DOT_COLORS = ['bg-blue-400', 'bg-emerald-400', 'bg-amber-400', 'bg-purple-400', 'bg-pink-400', 'bg-cyan-400']
const renamingPath = ref<string | null>(null)
const renameInput = ref('')

interface NavItem {
  path: string
  label: string
  icon: Component
  children?: Array<{ path: string; label: string; dotColor: string }>
}

const navItems = computed<NavItem[]>(() => [
  { path: '/', label: '首页', icon: Home },
  { path: '/software', label: '软件舱', icon: Package },
  { path: '/workspaces', label: '工作区', icon: FolderOpen, children: workspaceDirEntries.value },
  { path: '/logs', label: '日志', icon: ClipboardList },
  { path: '/settings', label: '设置', icon: Settings },
])

const expandedNav = ref<Set<string>>(new Set(['/workspaces']))

function isNavActive(path: string): boolean {
  if (path === '/') return route.path === '/'
  return route.path === path || route.path.startsWith(path + '/')
}

function handleExpandableClick(item: NavItem) {
  // 同时导航 + 切换展开
  if (route.path !== item.path) {
    router.push(item.path)
  }
  const newSet = new Set(expandedNav.value)
  if (newSet.has(item.path)) {
    newSet.delete(item.path)
  } else {
    newSet.add(item.path)
  }
  expandedNav.value = newSet
}

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
    await llmHealthCheck()
    llmConfigured.value = true
  } catch {
    llmConfigured.value = false
  }
}

async function loadWorkspaceDirs() {
  try {
    const { data } = await getAllowedDirs()
    allDirEntries.value = data.allowed_dirs
    workspaceDirEntries.value = data.allowed_dirs
      .filter((d: DirEntry) => d.type === 'workspace')
      .map((d: DirEntry, i: number) => {
        // 优先使用自定义标签，否则取目录名
        let label = d.label?.trim()
        if (!label) {
          const segments = d.path.replace(/[\\/]+$/, '').split(/[\\/]/)
          label = segments[segments.length - 1] || d.path
        }
        return { path: d.path, label, dotColor: DOT_COLORS[i % DOT_COLORS.length] }
      })
  } catch { /* ignore */ }
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
  loadWorkspaceDirs()
}

function startRename(childPath: string, currentLabel: string) {
  renamingPath.value = childPath
  renameInput.value = currentLabel
}

async function confirmRename(childPath: string) {
  const newLabel = renameInput.value.trim()
  renamingPath.value = null

  // 更新 allDirEntries 中对应条目的 label
  const updated = allDirEntries.value.map(d => {
    if (d.path === childPath) {
      // 如果新标签等于目录名本身，则清除自定义标签
      const segments = d.path.replace(/[\\/]+$/, '').split(/[\\/]/)
      const dirName = segments[segments.length - 1] || d.path
      if (!newLabel || newLabel === dirName) {
        const { label: _removed, ...rest } = d as DirEntry & { label?: string }
        return rest as DirEntry
      }
      return { ...d, label: newLabel }
    }
    return d
  })

  try {
    await updateAllowedDirs(updated)
    allDirEntries.value = updated
    // 更新侧边栏显示
    await loadWorkspaceDirs()
  } catch { /* ignore */ }
}

function cancelRename() {
  renamingPath.value = null
}

onMounted(() => {
  checkStatus()
  checkInitStatus()
  loadWorkspaceDirs()
  // 每 30 秒检查一次
  setInterval(checkStatus, 30_000)
})
</script>
