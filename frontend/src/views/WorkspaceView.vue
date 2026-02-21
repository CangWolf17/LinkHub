<template>
  <div>
    <div class="flex items-center justify-between mb-6">
      <h2 class="text-xl font-bold text-gray-900">工作区</h2>
      <div class="flex items-center gap-2">
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
    <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      <WorkspaceCard
        v-for="ws in items"
        :key="ws.id"
        :workspace="ws"
        @open-dir="handleOpenDir"
        @edit="openEditDialog"
        @delete="handleDelete"
      />
    </div>

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
import { ref, onMounted } from 'vue'
import { getWorkspaceList, deleteWorkspace, openDir, cleanupDeadWorkspaces } from '@/api'
import type { Workspace } from '@/api'
import WorkspaceCard from '@/components/WorkspaceCard.vue'
import WorkspaceDialog from '@/components/WorkspaceDialog.vue'

const items = ref<Workspace[]>([])
const loading = ref(true)
const filterStatus = ref('')
const dialogOpen = ref(false)
const editingWorkspace = ref<Workspace | null>(null)

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
