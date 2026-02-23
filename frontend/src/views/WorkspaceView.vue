<template>
  <div>
    <div class="flex items-center justify-between mb-6">
      <div class="flex items-center gap-3">
        <!-- 状态筛选（标题左侧） -->
        <select
          v-model="filterStatus"
          class="px-2 py-1.5 text-xs border border-gray-200 rounded-lg bg-white text-gray-600 focus:outline-none focus:ring-1 focus:ring-blue-400"
          @change="loadList"
        >
          <option value="">全部状态</option>
          <option value="not_started">未开始</option>
          <option value="active">进行中</option>
          <option value="completed">已完成</option>
          <option value="archived">已归档</option>
        </select>
        <h2 class="text-xl font-bold text-gray-900">工作区</h2>
        <span v-if="dirFilter" class="text-xs text-gray-400 bg-gray-100 px-2 py-0.5 rounded-full truncate max-w-[200px]" :title="dirFilter">
          {{ dirFilterLabel }}
        </span>
      </div>
      <div class="flex items-center gap-2">
        <!-- 新建工作区 -->
        <button
          class="px-3 py-1.5 text-xs font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors"
          @click="openCreateDialog"
        >
          + 新建工作区
        </button>
        <!-- AI 批量 -->
        <button
          v-if="itemsWithoutDescription.length > 0 && !bulkGenerating"
          class="px-3 py-1.5 text-xs font-medium text-purple-600 bg-purple-50 rounded-lg hover:bg-purple-100 transition-colors"
          @click="bulkGenerate"
        >
          AI 批量清洗 ({{ itemsWithoutDescription.length }})
        </button>
        <button
          v-if="bulkGenerating"
          class="px-3 py-1.5 text-xs font-medium text-red-600 bg-red-50 rounded-lg hover:bg-red-100 transition-colors"
          @click="stopBulkGenerate"
        >
          停止生成 ({{ bulkProgress }}/{{ bulkTotal }})
        </button>
        <!-- 时间分组 -->
        <select
          v-model="groupBy"
          class="px-2 py-1.5 text-xs border border-gray-200 rounded-lg bg-white text-gray-600 focus:outline-none focus:ring-1 focus:ring-blue-400"
        >
          <option value="none">不分组</option>
          <option value="year">按年分组</option>
          <option value="month">按月分组</option>
        </select>
        <!-- 多选模式切换 -->
        <button
          class="px-3 py-1.5 text-xs font-medium rounded-lg transition-colors"
          :class="selectMode
            ? 'text-white bg-blue-600 hover:bg-blue-700'
            : 'text-blue-600 bg-blue-50 hover:bg-blue-100'"
          @click="toggleSelectMode"
        >
          {{ selectMode ? '取消选择' : '多选' }}
        </button>
        <!-- 多选模式下立即显示的批量操作按钮 -->
        <template v-if="selectMode">
          <!-- 全选 -->
          <button
            class="px-3 py-1.5 text-xs font-medium text-gray-600 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
            @click="toggleSelectAll"
          >
            {{ selectedIds.size === items.length ? '取消全选' : '全选' }}
          </button>
          <!-- 批量删除按钮 -->
          <button
            class="px-3 py-1.5 text-xs font-medium text-white bg-red-500 rounded-lg hover:bg-red-600 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            :disabled="selectedIds.size === 0"
            @click="batchDelete"
          >
            删除选中 ({{ selectedIds.size }})
          </button>
          <!-- 批量设置状态 -->
          <select
            class="text-xs border border-gray-300 rounded-lg px-2 py-1.5 focus:outline-none focus:ring-2 focus:ring-blue-500 text-gray-600 disabled:opacity-40 disabled:cursor-not-allowed"
            :disabled="selectedIds.size === 0"
            @change="handleBatchStatus($event)"
          >
            <option value="" selected disabled>批量设置状态...</option>
            <option value="not_started">未开始</option>
            <option value="active">进行中</option>
            <option value="completed">已完成</option>
            <option value="archived">已归档</option>
          </select>
        </template>
        <!-- 清理死链 -->
        <button
          class="p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
          title="清理死链"
          @click="cleanupDead"
        >
          <Unlink :size="20" />
        </button>
      </div>
    </div>

    <!-- 卡片网格 -->
    <div v-if="loading" class="text-center py-12 text-gray-500 text-sm">加载中...</div>
    <div v-else-if="items.length === 0" class="text-center py-12 text-gray-400 text-sm">
      暂无工作区记录
    </div>
    <template v-else>
      <!-- 非归档内容 -->
      <template v-if="groupBy === 'none'">
        <div v-if="activeItems.length > 0" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <WorkspaceCard
            v-for="ws in activeItems"
            :key="ws.id"
            :workspace="ws"
            :selectable="selectMode"
            :selected="selectedIds.has(ws.id)"
            @open-dir="handleOpenDir"
            @edit="openEditDialog"
            @delete="handleDelete"
            @toggle-select="toggleSelect"
          />
        </div>
        <div v-else-if="archivedItems.length > 0" class="text-center py-8 text-gray-400 text-sm">
          所有工作区均已归档
        </div>
      </template>

      <!-- 时间分组模式 -->
      <template v-else>
        <div v-if="groupedActive.length === 0 && archivedItems.length > 0" class="text-center py-8 text-gray-400 text-sm">
          所有工作区均已归档
        </div>
        <div v-for="group in groupedActive" :key="group.label" class="mb-6">
          <button
            class="flex items-center gap-2 mb-3 text-sm font-semibold text-gray-500 hover:text-gray-700 transition-colors"
            @click="toggleGroup(group.label)"
          >
            <ChevronDown
              :size="14"
              class="transition-transform duration-200"
              :class="collapsedGroups.has(group.label) ? '-rotate-90' : ''"
            />
            {{ group.label }} ({{ group.items.length }})
          </button>
          <div v-if="!collapsedGroups.has(group.label)" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <WorkspaceCard
              v-for="ws in group.items"
              :key="ws.id"
              :workspace="ws"
              :selectable="selectMode"
              :selected="selectedIds.has(ws.id)"
              @open-dir="handleOpenDir"
              @edit="openEditDialog"
              @delete="handleDelete"
              @toggle-select="toggleSelect"
            />
          </div>
        </div>
      </template>

      <!-- 归档折叠区域 -->
      <div v-if="archivedItems.length > 0" class="mt-6">
        <button
          class="w-full flex items-center justify-center gap-2 py-2.5 px-4 bg-gray-100 hover:bg-gray-200 text-gray-500 rounded-lg transition-colors text-sm font-medium border border-gray-200"
          @click="showArchived = !showArchived"
        >
          <ChevronDown
            :size="16"
            class="transition-transform duration-200"
            :class="showArchived ? 'rotate-180' : ''"
          />
          已归档 ({{ archivedItems.length }})
        </button>
        <transition
          enter-active-class="transition-all duration-300 ease-out"
          enter-from-class="opacity-0 max-h-0"
          enter-to-class="opacity-100 max-h-[2000px]"
          leave-active-class="transition-all duration-200 ease-in"
          leave-from-class="opacity-100 max-h-[2000px]"
          leave-to-class="opacity-0 max-h-0"
        >
          <div v-if="showArchived" class="mt-4 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 overflow-hidden">
            <WorkspaceCard
              v-for="ws in archivedItems"
              :key="ws.id"
              :workspace="ws"
              :selectable="selectMode"
              :selected="selectedIds.has(ws.id)"
              @open-dir="handleOpenDir"
              @edit="openEditDialog"
              @delete="handleDelete"
              @toggle-select="toggleSelect"
            />
          </div>
        </transition>
      </div>
    </template>

    <!-- 创建/编辑弹窗 -->
    <WorkspaceDialog
      v-if="dialogOpen"
      :workspace="editingWorkspace"
      @close="dialogOpen = false"
      @saved="onSaved"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getWorkspaceList, deleteWorkspace, openDir, cleanupDeadWorkspaces, batchDeleteWorkspaces, batchUpdateWorkspaceStatus, getLlmConfig, aiWorkspaceFillForm, updateWorkspace } from '@/api'
import type { Workspace } from '@/api'
import WorkspaceCard from '@/components/WorkspaceCard.vue'
import WorkspaceDialog from '@/components/WorkspaceDialog.vue'
import { Unlink, ChevronDown } from 'lucide-vue-next'

const route = useRoute()
const router = useRouter()

const allItems = ref<Workspace[]>([])
const loading = ref(true)
const filterStatus = ref('')
const dialogOpen = ref(false)
const editingWorkspace = ref<Workspace | null>(null)

// 按目录过滤
const dirFilter = computed(() => (route.query.dir as string) || '')
const dirFilterLabel = computed(() => {
  if (!dirFilter.value) return ''
  const segments = dirFilter.value.replace(/[\\/]+$/, '').split(/[\\/]/)
  return segments[segments.length - 1] || dirFilter.value
})

// 最终展示的列表：先按目录过滤，再按状态过滤
const items = computed(() => {
  if (!dirFilter.value) return allItems.value
  const prefix = dirFilter.value.replace(/[\\/]+$/, '').toLowerCase()
  return allItems.value.filter((w) => {
    const wp = w.directory_path.replace(/[\\/]+$/, '').toLowerCase()
    return wp === prefix || wp.startsWith(prefix + '\\') || wp.startsWith(prefix + '/')
  })
})

// 当 dir 查询参数变化时重新刷新（触发 computed 即可）
watch(() => route.query.dir, () => {
  // items 是 computed，自动更新
  // 但需要重置选中等状态
  selectedIds.value = new Set()
})

// 多选状态
const selectMode = ref(false)
const selectedIds = ref<Set<string>>(new Set())

// 归档折叠
const showArchived = ref(false)

// 时间分组
const groupBy = ref<'none' | 'year' | 'month'>(
  (localStorage.getItem('linkhub_ws_groupBy') as 'none' | 'year' | 'month') || 'none'
)
const collapsedGroups = ref<Set<string>>(new Set())

watch(groupBy, (v) => {
  localStorage.setItem('linkhub_ws_groupBy', v)
  collapsedGroups.value = new Set()
})

function toggleGroup(label: string) {
  const newSet = new Set(collapsedGroups.value)
  if (newSet.has(label)) {
    newSet.delete(label)
  } else {
    newSet.add(label)
  }
  collapsedGroups.value = newSet
}

interface WorkspaceGroup {
  label: string
  sortKey: string
  items: Workspace[]
}

const groupedActive = computed<WorkspaceGroup[]>(() => {
  if (groupBy.value === 'none') return []
  const groups = new Map<string, { label: string; sortKey: string; items: Workspace[] }>()

  for (const ws of activeItems.value) {
    const d = new Date(ws.created_at)
    let label: string
    let sortKey: string
    if (groupBy.value === 'year') {
      const y = d.getFullYear()
      label = `${y} 年`
      sortKey = `${y}`
    } else {
      const y = d.getFullYear()
      const m = d.getMonth() + 1
      label = `${y} 年 ${m} 月`
      sortKey = `${y}-${String(m).padStart(2, '0')}`
    }
    if (!groups.has(sortKey)) {
      groups.set(sortKey, { label, sortKey, items: [] })
    }
    groups.get(sortKey)!.items.push(ws)
  }

  return Array.from(groups.values()).sort((a, b) => b.sortKey.localeCompare(a.sortKey))
})

// 将工作区分为非归档和已归档两组（仅在未过滤归档状态时分组）
const shouldSeparateArchived = computed(() => filterStatus.value !== 'archived')
const activeItems = computed(() =>
  shouldSeparateArchived.value ? items.value.filter((w) => w.status !== 'archived') : items.value
)
const archivedItems = computed(() =>
  shouldSeparateArchived.value ? items.value.filter((w) => w.status === 'archived') : []
)

function toggleSelectMode() {
  selectMode.value = !selectMode.value
  if (!selectMode.value) {
    selectedIds.value = new Set()
  }
}

function toggleSelect(id: string) {
  const newSet = new Set(selectedIds.value)
  if (newSet.has(id)) {
    newSet.delete(id)
  } else {
    newSet.add(id)
  }
  selectedIds.value = newSet
}

function toggleSelectAll() {
  if (selectedIds.value.size === items.value.length) {
    selectedIds.value = new Set()
  } else {
    selectedIds.value = new Set(items.value.map((w) => w.id))
  }
}

async function batchDelete() {
  const count = selectedIds.value.size
  if (count === 0) return
  if (!confirm(`确定删除选中的 ${count} 条工作区记录吗？（仅删除数据库记录，不删除本地文件）`)) return
  try {
    const ids = Array.from(selectedIds.value)
    const { data } = await batchDeleteWorkspaces(ids)
    alert(`已删除 ${data.deleted_count} 条记录`)
    selectedIds.value = new Set()
    selectMode.value = false
    await loadList()
  } catch {
    alert('批量删除失败，请重试')
  }
}

async function handleBatchStatus(event: Event) {
  const target = event.target as HTMLSelectElement
  const newStatus = target.value
  if (!newStatus) return
  target.value = '' // 重置下拉

  const statusLabels: Record<string, string> = {
    not_started: '未开始',
    active: '进行中',
    completed: '已完成',
    archived: '已归档',
  }
  const count = selectedIds.value.size
  if (!confirm(`确定将选中的 ${count} 个工作区状态设为「${statusLabels[newStatus] || newStatus}」吗？`)) return
  try {
    const ids = Array.from(selectedIds.value)
    const { data } = await batchUpdateWorkspaceStatus(ids, newStatus)
    alert(`已更新 ${data.updated_count} 条记录状态为「${statusLabels[newStatus] || newStatus}」`)
    selectedIds.value = new Set()
    selectMode.value = false
    await loadList()
  } catch {
    alert('批量更新状态失败，请重试')
  }
}

async function loadList() {
  loading.value = true
  try {
    const params: Record<string, string> = {}
    if (filterStatus.value) params.status = filterStatus.value
    const { data } = await getWorkspaceList(params)
    allItems.value = data.items
  } catch { /* ignore */ } finally {
    loading.value = false
  }
}

function openCreateDialog() {
  editingWorkspace.value = null
  dialogOpen.value = true
}

function openEditDialog(ws: Workspace) {
  editingWorkspace.value = ws
  dialogOpen.value = true
}

async function onSaved() {
  dialogOpen.value = false
  await loadList()
}

async function handleOpenDir(path: string) {
  try {
    await openDir(path)
  } catch (e: unknown) {
    const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '打开失败'
    alert(detail)
  }
}

async function handleDelete(id: string) {
  if (!confirm('确定删除这个工作区记录吗?')) return
  try {
    await deleteWorkspace(id)
    allItems.value = allItems.value.filter((w) => w.id !== id)
  } catch { /* ignore */ }
}

async function cleanupDead() {
  if (!confirm('将删除所有路径失效的工作区记录，确定?')) return
  try {
    const { data } = await cleanupDeadWorkspaces()
    alert(`已清理 ${data.removed_count} 条死链记录`)
    await loadList()
  } catch { /* ignore */ }
}

// 批量生成状态
const bulkGenerating = ref(false)
const bulkProgress = ref(0)
const bulkTotal = ref(0)
let bulkAbort = false
const workspaceBlacklist = ref<string[]>([])

const itemsWithoutDescription = computed(() =>
  items.value.filter((w) => !w.description && !w.is_missing)
)

function stopBulkGenerate() {
  bulkAbort = true
}

async function bulkGenerate() {
  // 加载黑名单
  try {
    const { data } = await getLlmConfig()
    workspaceBlacklist.value = data.ai_blacklist_workspace || []
  } catch { /* ignore */ }
  const blackSet = new Set(workspaceBlacklist.value.map(n => n.toLowerCase()))

  const targets = itemsWithoutDescription.value.filter(w => !blackSet.has(w.name.toLowerCase()))
  const skipped = itemsWithoutDescription.value.length - targets.length
  if (targets.length === 0) {
    alert(skipped > 0 ? `所有无描述工作区均在黑名单中（${skipped} 个已跳过）` : '没有需要清洗的工作区')
    return
  }
  const skipMsg = skipped > 0 ? `（${skipped} 个黑名单已跳过）` : ''
  if (!confirm(`将为 ${targets.length} 个工作区执行 AI 清洗（名称清洗 + 生成描述）${skipMsg}，确定?`)) return

  bulkGenerating.value = true
  bulkTotal.value = targets.length
  bulkProgress.value = 0
  bulkAbort = false

  let successCount = 0
  let failCount = 0

  for (const ws of targets) {
    if (bulkAbort) break
    try {
      const { data } = await aiWorkspaceFillForm(ws.directory_path)
      if (data.success) {
        // 将 AI 清洗结果（名称 + 描述）写入数据库
        const updates: Record<string, string> = {}
        if (data.name && data.name !== ws.name) updates.name = data.name
        if (data.description) updates.description = data.description
        if (data.deadline && !ws.deadline) updates.deadline = data.deadline

        if (Object.keys(updates).length > 0) {
          const { data: updated } = await updateWorkspace(ws.id, updates)
          const idx = allItems.value.findIndex((w) => w.id === ws.id)
          if (idx !== -1) {
            allItems.value[idx] = { ...allItems.value[idx], ...updated }
          }
        }
        successCount++
      } else {
        failCount++
      }
    } catch {
      failCount++
    }
    bulkProgress.value++
  }

  bulkGenerating.value = false
  const stoppedMsg = bulkAbort ? '（已手动停止）' : ''
  alert(`批量清洗完成${stoppedMsg}：成功 ${successCount} 个，失败 ${failCount} 个`)
}

// 页面离开时自动停止批量生成
onBeforeUnmount(() => {
  bulkAbort = true
})

// 搜索高亮: 滚动到指定卡片并应用动画
function scrollToHighlight(id: string) {
  nextTick(() => {
    const el = document.querySelector(`[data-id="${id}"]`) as HTMLElement | null
    if (!el) return
    el.scrollIntoView({ behavior: 'smooth', block: 'center' })
    el.classList.add('search-highlight')
    setTimeout(() => el.classList.remove('search-highlight'), 2000)
    // 清除 query param
    router.replace({ query: { ...route.query, highlight: undefined } })
  })
}

watch(() => route.query.highlight, (id) => {
  if (id && typeof id === 'string') {
    // 确保归档区域展开以找到卡片
    const ws = allItems.value.find(w => w.id === id)
    if (ws && ws.status === 'archived') {
      showArchived.value = true
    }
    scrollToHighlight(id)
  }
})

onMounted(async () => {
  await loadList()
  if (route.query.highlight) {
    const ws = allItems.value.find(w => w.id === route.query.highlight)
    if (ws && ws.status === 'archived') {
      showArchived.value = true
    }
    scrollToHighlight(route.query.highlight as string)
  }
})
</script>
