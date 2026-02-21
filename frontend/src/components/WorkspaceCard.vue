<template>
  <div
    class="bg-white rounded-xl border shadow-sm overflow-hidden transition-all hover:shadow-md"
    :class="cardBorderClass"
  >
    <div class="p-4">
      <!-- 标题行 -->
      <div class="flex items-start justify-between gap-2 mb-2">
        <div class="flex items-center gap-2 min-w-0 flex-1">
          <span class="text-lg flex-shrink-0">{{ statusIcon }}</span>
          <h3
            class="text-sm font-semibold truncate"
            :class="workspace.is_missing ? 'text-gray-400 line-through' : 'text-gray-900'"
            :title="workspace.name"
          >
            {{ workspace.name }}
          </h3>
        </div>

        <!-- 操作 -->
        <div class="flex items-center gap-1 flex-shrink-0">
          <button
            v-if="!workspace.is_missing"
            class="p-1.5 text-gray-500 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
            title="打开目录"
            @click="$emit('openDir', workspace.directory_path)"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 19a2 2 0 01-2-2V7a2 2 0 012-2h4l2 2h4a2 2 0 012 2v1M5 19h14a2 2 0 002-2v-5a2 2 0 00-2-2H9a2 2 0 00-2 2v5a2 2 0 01-2 2z" />
            </svg>
          </button>
          <button
            class="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
            title="编辑"
            @click="$emit('edit', workspace)"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
            </svg>
          </button>
          <button
            class="p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
            title="删除"
            @click="$emit('delete', workspace.id)"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
          </button>
        </div>
      </div>

      <!-- 描述 -->
      <p v-if="workspace.description" class="text-xs text-gray-500 mb-3 line-clamp-2">
        {{ workspace.description }}
      </p>

      <!-- 路径 -->
      <div class="text-[11px] text-gray-400 font-mono truncate mb-2" :title="workspace.directory_path">
        {{ workspace.directory_path }}
      </div>

      <!-- Deadline 和状态 -->
      <div class="flex items-center gap-2 flex-wrap">
        <!-- 状态标签 -->
        <span
          class="text-[10px] px-2 py-0.5 rounded-full font-medium"
          :class="statusBadgeClass"
        >
          {{ statusLabel }}
        </span>

        <!-- Deadline -->
        <span
          v-if="workspace.deadline"
          class="text-[10px] px-2 py-0.5 rounded-full font-medium"
          :class="deadlineClass"
        >
          {{ deadlineLabel }}
        </span>

        <!-- 死链 -->
        <span
          v-if="workspace.is_missing"
          class="text-[10px] px-2 py-0.5 bg-red-50 text-red-600 rounded-full font-medium"
        >
          路径失效
        </span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { Workspace } from '@/api'

const props = defineProps<{
  workspace: Workspace
}>()

defineEmits<{
  openDir: [path: string]
  edit: [workspace: Workspace]
  delete: [id: string]
}>()

const statusIcon = computed(() => {
  if (props.workspace.is_missing) return '⚠️'
  switch (props.workspace.status) {
    case 'not_started': return '⏳'
    case 'active': return '🟢'
    case 'completed': return '✅'
    case 'archived': return '📁'
    default: return '📂'
  }
})

const statusLabel = computed(() => {
  switch (props.workspace.status) {
    case 'not_started': return '未开始'
    case 'active': return '进行中'
    case 'completed': return '已完成'
    case 'archived': return '已归档'
    default: return props.workspace.status
  }
})

const statusBadgeClass = computed(() => {
  switch (props.workspace.status) {
    case 'not_started': return 'bg-yellow-50 text-yellow-700'
    case 'active': return 'bg-green-50 text-green-700'
    case 'completed': return 'bg-blue-50 text-blue-700'
    case 'archived': return 'bg-gray-100 text-gray-600'
    default: return 'bg-gray-100 text-gray-600'
  }
})

const cardBorderClass = computed(() => {
  if (props.workspace.is_missing) return 'border-gray-300 opacity-60'
  if (deadlineDaysLeft.value !== null) {
    if (deadlineDaysLeft.value < 0) return 'border-red-300'
    if (deadlineDaysLeft.value <= 3) return 'border-orange-300'
  }
  return 'border-gray-200'
})

const deadlineDaysLeft = computed(() => {
  if (!props.workspace.deadline) return null
  const deadline = new Date(props.workspace.deadline)
  const now = new Date()
  const diff = deadline.getTime() - now.getTime()
  return Math.ceil(diff / (1000 * 60 * 60 * 24))
})

const deadlineClass = computed(() => {
  if (deadlineDaysLeft.value === null) return ''
  if (deadlineDaysLeft.value < 0) return 'bg-red-100 text-red-700'
  if (deadlineDaysLeft.value <= 3) return 'bg-orange-100 text-orange-700'
  return 'bg-gray-100 text-gray-600'
})

const deadlineLabel = computed(() => {
  if (deadlineDaysLeft.value === null) return ''
  if (deadlineDaysLeft.value < 0) return `已超期 ${Math.abs(deadlineDaysLeft.value)} 天`
  if (deadlineDaysLeft.value === 0) return '今天截止'
  if (deadlineDaysLeft.value <= 3) return `剩余 ${deadlineDaysLeft.value} 天`
  const d = new Date(props.workspace.deadline!)
  return d.toLocaleDateString('zh-CN')
})
</script>
