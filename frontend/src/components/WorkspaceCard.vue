<template>
  <div
    :data-id="workspace.id"
    class="bg-white rounded-xl border shadow-sm overflow-hidden transition-all hover:shadow-md"
    :class="cardBorderClass"
    @contextmenu="openContextMenu"
  >
    <div class="p-4">
      <!-- 标题行 -->
      <div class="flex items-start justify-between gap-2 mb-2">
        <div class="flex items-center gap-2 min-w-0 flex-1">
          <!-- 多选复选框 -->
          <input
            v-if="selectable"
            type="checkbox"
            :checked="selected"
            class="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500 flex-shrink-0 cursor-pointer"
            @change="$emit('toggle-select', workspace.id)"
          />
          <span v-if="workspace.is_missing" class="flex-shrink-0 text-base">&#9888;&#65039;</span>
          <span v-else class="flex-shrink-0 text-base">{{ statusEmoji }}</span>
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
            <FolderOpen :size="16" />
          </button>
          <button
            class="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
            title="编辑"
            @click="$emit('edit', workspace)"
          >
            <Pencil :size="16" />
          </button>
          <button
            class="p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
            title="删除"
            @click="$emit('delete', workspace.id)"
          >
            <Trash2 :size="16" />
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

        <!-- 目录树展开按钮 -->
        <button
          v-if="!workspace.is_missing"
          class="ml-auto p-0.5 text-gray-300 hover:text-gray-500 transition-colors"
          :title="treeExpanded ? '收起目录树' : '展开目录树'"
          @click="treeExpanded = !treeExpanded"
        >
          <ChevronDown
            :size="14"
            class="transition-transform duration-200"
            :class="treeExpanded ? 'rotate-180' : ''"
          />
        </button>
      </div>
    </div>

    <!-- 内嵌目录树 -->
    <div v-if="treeExpanded" class="border-t border-gray-100 px-3 py-2 max-h-64 overflow-y-auto bg-gray-50/50">
      <DirectoryTree :root-path="workspace.directory_path" />
    </div>
  </div>

  <!-- 右键菜单 -->
  <ContextMenu ref="contextMenuRef" :items="contextMenuItems" />
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import type { Workspace } from '@/api'
import DirectoryTree from '@/components/DirectoryTree.vue'
import ContextMenu from '@/components/ContextMenu.vue'
import type { ContextMenuItem } from '@/components/ContextMenu.vue'
import { FolderOpen, Pencil, Trash2, ChevronDown } from 'lucide-vue-next'

const props = defineProps<{
  workspace: Workspace
  selectable?: boolean
  selected?: boolean
}>()

const emit = defineEmits<{
  openDir: [path: string]
  edit: [workspace: Workspace]
  delete: [id: string]
  'toggle-select': [id: string]
  'change-status': [id: string, status: string]
}>()

const treeExpanded = ref(false)

const isArchived = computed(() => props.workspace.status === 'archived')

const statusEmoji = computed(() => {
  switch (props.workspace.status) {
    case 'not_started': return '\u23F3'  // ⏳ hourglass
    case 'active': return '\u{1F7E2}'    // 🟢 green circle
    case 'completed': return '\u{1F55B}'  // 🕛 clock
    case 'archived': return '\u{1F4E6}'   // 📦 package
    default: return '\u{1F4C1}'           // 📁 folder
  }
})

const statusLabel = computed(() => {
  switch (props.workspace.status) {
    case 'not_started': return '未开始'
    case 'active': return '进行中'
    case 'completed': return '已过期'
    case 'archived': return '已归档'
    default: return props.workspace.status
  }
})

const statusBadgeClass = computed(() => {
  switch (props.workspace.status) {
    case 'not_started': return 'bg-slate-100 text-slate-600'
    case 'active': return 'bg-emerald-50 text-emerald-700'
    case 'completed': return 'bg-slate-100 text-slate-500'
    case 'archived': return 'bg-gray-100 text-gray-500'
    default: return 'bg-gray-100 text-gray-600'
  }
})

const deadlineDaysLeft = computed(() => {
  if (!props.workspace.deadline) return null
  const deadline = new Date(props.workspace.deadline)
  const now = new Date()
  const diff = deadline.getTime() - now.getTime()
  return Math.ceil(diff / (1000 * 60 * 60 * 24))
})

// 分级截止提醒样式（归档状态抑制所有紧急样式）
const cardBorderClass = computed(() => {
  if (props.workspace.is_missing) return 'border-gray-300 opacity-60'
  if (isArchived.value) return 'border-gray-200'
  if (deadlineDaysLeft.value !== null) {
    if (deadlineDaysLeft.value < 0) return 'border-red-300'
    if (deadlineDaysLeft.value <= 3) return 'border-orange-300'
    if (deadlineDaysLeft.value <= 7) return 'border-amber-200'
  }
  return 'border-gray-200'
})

const deadlineClass = computed(() => {
  if (deadlineDaysLeft.value === null) return ''
  // 归档状态：统一使用柔和灰色，不显示紧急配色
  if (isArchived.value) return 'bg-gray-100 text-gray-500'
  // 分级紧急度配色
  if (deadlineDaysLeft.value < 0) return 'bg-red-100 text-red-700'
  if (deadlineDaysLeft.value <= 3) return 'bg-orange-100 text-orange-700'
  if (deadlineDaysLeft.value <= 7) return 'bg-amber-50 text-amber-700'
  if (deadlineDaysLeft.value <= 14) return 'bg-blue-50 text-blue-600'
  return 'bg-gray-100 text-gray-600'
})

const deadlineLabel = computed(() => {
  if (deadlineDaysLeft.value === null) return ''
  // 归档状态：只显示日期，不显示超期警告
  if (isArchived.value) {
    const d = new Date(props.workspace.deadline!)
    return d.toLocaleDateString('zh-CN')
  }
  if (deadlineDaysLeft.value < 0) return `已超期 ${Math.abs(deadlineDaysLeft.value)} 天`
  if (deadlineDaysLeft.value === 0) return '今天截止'
  if (deadlineDaysLeft.value <= 3) return `剩余 ${deadlineDaysLeft.value} 天`
  if (deadlineDaysLeft.value <= 7) return `剩余 ${deadlineDaysLeft.value} 天`
  if (deadlineDaysLeft.value <= 14) return `剩余 ${deadlineDaysLeft.value} 天`
  const d = new Date(props.workspace.deadline!)
  return d.toLocaleDateString('zh-CN')
})

// ── 右键菜单 ──────────────────────────────────────────────
const contextMenuRef = ref<InstanceType<typeof ContextMenu> | null>(null)

const statusOptions: Array<{ value: string; label: string; emoji: string }> = [
  { value: 'not_started', label: '未开始', emoji: '\u23F3' },
  { value: 'active', label: '进行中', emoji: '\u{1F7E2}' },
  { value: 'completed', label: '已过期', emoji: '\u{1F55B}' },
  { value: 'archived', label: '已归档', emoji: '\u{1F4E6}' },
]

const contextMenuItems = computed<ContextMenuItem[]>(() => {
  const items: ContextMenuItem[] = []

  // 打开目录
  if (!props.workspace.is_missing) {
    items.push({
      label: '打开目录',
      icon: FolderOpen,
      action: () => emit('openDir', props.workspace.directory_path),
    })
  }

  // 编辑
  items.push({
    label: '编辑',
    icon: Pencil,
    action: () => emit('edit', props.workspace),
  })

  items.push({ separator: true })

  // 设置状态（列出所有可选状态，排除当前状态）
  for (const opt of statusOptions) {
    if (opt.value === props.workspace.status) continue
    items.push({
      label: `设为「${opt.label}」`,
      emoji: opt.emoji,
      action: () => emit('change-status', props.workspace.id, opt.value),
    })
  }

  items.push({ separator: true })

  // 删除
  items.push({
    label: '删除',
    icon: Trash2,
    danger: true,
    action: () => emit('delete', props.workspace.id),
  })

  return items
})

function openContextMenu(e: MouseEvent) {
  contextMenuRef.value?.open(e)
}
</script>
