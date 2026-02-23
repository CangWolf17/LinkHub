<template>
  <div>
    <h2 class="text-xl font-bold text-gray-900 mb-6">首页</h2>

    <!-- 最近使用的软件 -->
    <section class="mb-8">
      <h3 class="text-sm font-semibold text-gray-500 mb-3">最近使用</h3>
      <div v-if="recentLoading" class="text-sm text-gray-400">加载中...</div>
      <div v-else-if="recentSoftware.length === 0" class="text-sm text-gray-400">暂无最近使用的软件</div>
      <div v-else class="flex gap-3 overflow-x-auto pb-2">
        <div
          v-for="sw in recentSoftware"
          :key="sw.id"
          class="flex-shrink-0 w-28 h-28 bg-white border border-gray-200 rounded-xl flex flex-col items-center justify-center gap-2 cursor-pointer hover:shadow-md hover:border-blue-300 transition-all group"
          :title="sw.name + (sw.description ? '\n' + sw.description : '')"
          @click="handleLaunch(sw)"
        >
          <span class="text-2xl">📦</span>
          <span class="text-[11px] font-medium text-gray-700 text-center px-2 truncate w-full group-hover:text-blue-600">{{ sw.name }}</span>
        </div>
      </div>
    </section>

    <!-- 即将到期的工作区 -->
    <section class="mb-8">
      <h3 class="text-sm font-semibold text-gray-500 mb-3">即将到期</h3>
      <div v-if="deadlineLoading" class="text-sm text-gray-400">加载中...</div>
      <div v-else-if="deadlineWorkspaces.length === 0" class="text-sm text-gray-400">暂无即将到期的工作区</div>
      <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <div
          v-for="ws in deadlineWorkspaces"
          :key="ws.id"
          class="bg-white border rounded-xl p-4 hover:shadow-md transition-all cursor-pointer"
          :class="deadlineClass(ws)"
          @click="goToWorkspace(ws.id)"
        >
          <div class="flex items-start justify-between mb-2">
            <h4 class="text-sm font-semibold text-gray-900 truncate flex-1">{{ ws.name }}</h4>
            <span
              class="ml-2 px-1.5 py-0.5 rounded text-[10px] font-bold uppercase flex-shrink-0"
              :class="deadlineBadgeClass(ws)"
            >
              {{ deadlineLabel(ws) }}
            </span>
          </div>
          <p v-if="ws.description" class="text-xs text-gray-500 line-clamp-2 mb-2">{{ ws.description }}</p>
          <div class="flex items-center gap-2 text-[11px] text-gray-400">
            <span>截止: {{ formatDate(ws.deadline!) }}</span>
            <span v-if="daysUntil(ws.deadline!) < 0" class="text-red-500 font-bold">已过期 {{ Math.abs(daysUntil(ws.deadline!)) }} 天</span>
            <span v-else-if="daysUntil(ws.deadline!) === 0" class="text-orange-500 font-bold">今天到期</span>
            <span v-else class="text-orange-500">剩余 {{ daysUntil(ws.deadline!) }} 天</span>
          </div>
        </div>
      </div>
    </section>

    <!-- 进行中的工作区 -->
    <section>
      <h3 class="text-sm font-semibold text-gray-500 mb-3">进行中的工作区</h3>
      <div v-if="activeLoading" class="text-sm text-gray-400">加载中...</div>
      <div v-else-if="activeWorkspaces.length === 0" class="text-sm text-gray-400">暂无进行中的工作区</div>
      <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <div
          v-for="ws in activeWorkspaces"
          :key="ws.id"
          class="bg-white border border-gray-200 rounded-xl p-4 hover:shadow-md transition-all cursor-pointer"
          @click="goToWorkspace(ws.id)"
        >
          <h4 class="text-sm font-semibold text-gray-900 truncate mb-1">{{ ws.name }}</h4>
          <p v-if="ws.description" class="text-xs text-gray-500 line-clamp-2 mb-2">{{ ws.description }}</p>
          <div class="text-[11px] text-gray-400">
            更新于 {{ formatRelative(ws.updated_at) }}
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getSoftwareList, getWorkspaceList, launchApp } from '@/api'
import type { Software, Workspace } from '@/api'

const router = useRouter()

const recentLoading = ref(true)
const deadlineLoading = ref(true)
const activeLoading = ref(true)

const allSoftware = ref<Software[]>([])
const allWorkspaces = ref<Workspace[]>([])

// 最近使用：有 last_used_at 的、未失效的，按最近使用时间排序，最多 12 个
const recentSoftware = computed(() =>
  allSoftware.value
    .filter((s) => s.last_used_at && !s.is_missing)
    .sort((a, b) => new Date(b.last_used_at!).getTime() - new Date(a.last_used_at!).getTime())
    .slice(0, 12)
)

// 即将到期：有 deadline 的、非 archived/completed、deadline 在 14 天内或已过期
const deadlineWorkspaces = computed(() => {
  const limit = 14 // 天
  return allWorkspaces.value
    .filter((w) => {
      if (!w.deadline) return false
      if (w.status === 'archived' || w.status === 'completed') return false
      const days = daysUntil(w.deadline)
      return days <= limit
    })
    .sort((a, b) => new Date(a.deadline!).getTime() - new Date(b.deadline!).getTime())
})

// 进行中的工作区
const activeWorkspaces = computed(() =>
  allWorkspaces.value
    .filter((w) => w.status === 'active' && !w.is_missing)
    .sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime())
    .slice(0, 9)
)

function daysUntil(dateStr: string): number {
  const target = new Date(dateStr)
  const now = new Date()
  // 只比较日期，不比较时间
  const targetDate = new Date(target.getFullYear(), target.getMonth(), target.getDate())
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  return Math.round((targetDate.getTime() - today.getTime()) / (1000 * 60 * 60 * 24))
}

function deadlineClass(ws: Workspace): string {
  const days = daysUntil(ws.deadline!)
  if (days < 0) return 'border-red-300 bg-red-50/50'
  if (days <= 3) return 'border-orange-300 bg-orange-50/50'
  if (days <= 7) return 'border-yellow-300 bg-yellow-50/30'
  return 'border-gray-200'
}

function deadlineBadgeClass(ws: Workspace): string {
  const days = daysUntil(ws.deadline!)
  if (days < 0) return 'bg-red-100 text-red-600'
  if (days <= 3) return 'bg-orange-100 text-orange-600'
  return 'bg-yellow-100 text-yellow-700'
}

function deadlineLabel(ws: Workspace): string {
  const days = daysUntil(ws.deadline!)
  if (days < 0) return '已过期'
  if (days === 0) return '今天'
  if (days <= 3) return '紧急'
  return '临近'
}

function formatDate(dateStr: string): string {
  const d = new Date(dateStr)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

function formatRelative(dateStr: string): string {
  const d = new Date(dateStr)
  const now = new Date()
  const diff = now.getTime() - d.getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 60) return `${mins} 分钟前`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours} 小时前`
  const days = Math.floor(hours / 24)
  if (days < 30) return `${days} 天前`
  return formatDate(dateStr)
}

async function handleLaunch(sw: Software) {
  if (!sw.executable_path) return
  try {
    await launchApp(sw.executable_path)
    // 重新加载以更新 last_used_at
    const { data } = await getSoftwareList()
    allSoftware.value = data.items
  } catch (e: unknown) {
    const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '启动失败'
    alert(detail)
  }
}

function goToWorkspace(id: string) {
  router.push({ path: '/workspaces', query: { highlight: id } })
}

onMounted(async () => {
  // 并行加载
  const [swRes, wsRes] = await Promise.allSettled([
    getSoftwareList(),
    getWorkspaceList(),
  ])

  if (swRes.status === 'fulfilled') {
    allSoftware.value = swRes.value.data.items
  }
  recentLoading.value = false

  if (wsRes.status === 'fulfilled') {
    allWorkspaces.value = wsRes.value.data.items
  }
  deadlineLoading.value = false
  activeLoading.value = false
})
</script>
