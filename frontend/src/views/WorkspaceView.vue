<template>
  <div>
    <div class="flex items-center justify-between mb-6">
      <h2 class="text-xl font-bold text-gray-900">工作区</h2>
      <div class="flex items-center gap-2">
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
        <!-- 批量删除按钮 -->
        <button
          v-if="selectMode && selectedIds.size > 0"
          class="px-3 py-1.5 text-xs font-medium text-white bg-red-500 rounded-lg hover:bg-red-600 transition-colors"
          @click="batchDelete"
        >
          删除选中 ({{ selectedIds.size }})
        </button>
        <!-- 批量设置状态 -->
        <select
          v-if="selectMode && selectedIds.size > 0"
          class="text-xs border border-gray-300 rounded-lg px-2 py-1.5 focus:outline-none focus:ring-2 focus:ring-blue-500 text-gray-600"
          @change="handleBatchStatus($event)"
        >
          <option value="" selected disabled>批量设置状态...</option>
          <option value="not_started">未开始</option>
          <option value="active">进行中</option>
          <option value="completed">已完成</option>
          <option value="archived">已归档</option>
        </select>
        <!-- 全选 -->
        <button
          v-if="selectMode"
          class="px-3 py-1.5 text-xs font-medium text-gray-600 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
          @click="toggleSelectAll"
        >
          {{ selectedIds.size === items.length ? '取消全选' : '全选' }}
        </button>
        <select
          v-model="filterStatus"
          class="text-xs border border-gray-300 rounded-lg px-2 py-1.5 focus:outline-none focus:ring-2 focus:ring-blue-500"
          @change="loadList"
        >
          <option value="">全部状态</option>
          <option value="not_started">未开始</option>
          <option value="active">进行中</option>
          <option value="completed">已完成</option>
          <option value="archived">已归档</option>
        </select>
        <button
          class="px-3 py-1.5 text-xs font-medium text-red-600 bg-red-50 rounded-lg hover:bg-red-100 transition-colors"
          @click="cleanupDead"
        >
          清理死链
        </button>
        <button
          class="px-3 py-1.5 text-xs font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors"
          @click="openCreateDialog"
        >
          + 新建工作区
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

      <!-- 归档折叠区域 -->
      <div v-if="archivedItems.length > 0" class="mt-6">
        <button
          class="w-full flex items-center justify-center gap-2 py-2.5 px-4 bg-gray-100 hover:bg-gray-200 text-gray-500 rounded-lg transition-colors text-sm font-medium border border-gray-200"
          @click="showArchived = !showArchived"
        >
          <svg
            class="w-4 h-4 transition-transform duration-200"
            :class="showArchived ? 'rotate-180' : ''"
            fill="none" stroke="currentColor" viewBox="0 0 24 24"
          >
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
          </svg>
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
import { ref, computed, onMounted } from 'vue'
import { getWorkspaceList, deleteWorkspace, openDir, cleanupDeadWorkspaces, batchDeleteWorkspaces, batchUpdateWorkspaceStatus } from '@/api'
import type { Workspace } from '@/api'
import WorkspaceCard from '@/components/WorkspaceCard.vue'
import WorkspaceDialog from '@/components/WorkspaceDialog.vue'

const items = ref<Workspace[]>([])
const loading = ref(true)
const filterStatus = ref('')
const dialogOpen = ref(false)
const editingWorkspace = ref<Workspace | null>(null)

// 多选状态
const selectMode = ref(false)
const selectedIds = ref<Set<string>>(new Set())

// 归档折叠
const showArchived = ref(false)

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
    items.value = data.items
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
    items.value = items.value.filter((w) => w.id !== id)
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

onMounted(loadList)
</script>
