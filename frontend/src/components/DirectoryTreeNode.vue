<template>
  <div>
    <!-- 当前条目 -->
    <div
      class="flex items-center gap-1.5 py-0.5 px-1 rounded hover:bg-gray-50 cursor-default select-none group"
      :style="{ paddingLeft: `${depth * 16 + 4}px` }"
      @click="toggle"
      @contextmenu.prevent="onContextMenu"
    >
      <!-- 展开/折叠箭头 (仅目录) -->
      <span v-if="item.is_dir" class="w-3.5 h-3.5 flex items-center justify-center flex-shrink-0">
        <ChevronRight
          :size="12"
          class="text-gray-400 transition-transform duration-150"
          :class="expanded ? 'rotate-90' : ''"
        />
      </span>
      <!-- 文件占位 -->
      <span v-else class="w-3.5 h-3.5 flex-shrink-0" />

      <!-- 图标 -->
      <span class="flex-shrink-0">
        <template v-if="item.is_dir">
          <span v-if="item.is_symlink" class="inline-flex items-center gap-0.5 text-purple-500" title="符号链接目录"><Link :size="12" /><Folder :size="12" /></span>
          <FolderOpen v-else-if="expanded" :size="12" class="text-yellow-500" />
          <Folder v-else :size="12" class="text-yellow-600" />
        </template>
        <template v-else>
          <span v-if="item.is_symlink" class="text-purple-500" title="符号链接文件"><Link :size="12" /></span>
          <File v-else :size="12" class="text-gray-400" />
        </template>
      </span>

      <!-- 名称 -->
      <span
        class="truncate"
        :class="[
          item.is_dir ? 'text-gray-700 font-medium' : 'text-gray-500',
          item.is_symlink ? 'italic' : '',
        ]"
        :title="item.path + (item.symlink_target ? ` → ${item.symlink_target}` : '')"
      >
        {{ item.name }}
      </span>

      <!-- 符号链接标记 -->
      <span v-if="item.is_symlink" class="text-[10px] text-purple-400 flex-shrink-0 ml-1">
        &#8594; {{ symlinkTargetName }}
      </span>

      <!-- 文件大小 -->
      <span v-if="!item.is_dir && item.size !== null" class="text-[10px] text-gray-300 ml-auto flex-shrink-0">
        {{ formatSize(item.size) }}
      </span>
    </div>

    <!-- 右键菜单 -->
    <Teleport to="body">
      <div
        v-if="ctxMenu.show"
        class="fixed z-[100] bg-white rounded-lg shadow-lg border border-gray-200 py-1 min-w-[160px]"
        :style="{ left: `${ctxMenu.x}px`, top: `${ctxMenu.y}px` }"
        @click.stop
      >
        <button
          v-if="item.is_dir && !item.is_symlink"
          class="w-full flex items-center gap-2 px-3 py-1.5 text-xs text-gray-700 hover:bg-purple-50 hover:text-purple-700 transition-colors text-left"
          @click="handleCreateSymlink"
        >
          <Link :size="14" />
          创建符号链接
        </button>
        <button
          class="w-full flex items-center gap-2 px-3 py-1.5 text-xs text-gray-700 hover:bg-gray-50 transition-colors text-left"
          @click="handleCopyPath"
        >
          <Clipboard :size="14" />
          复制路径
        </button>
      </div>
    </Teleport>

    <!-- 符号链接弹窗 -->
    <SymlinkDialog
      v-if="showSymlinkDialog"
      :source-path="item.path"
      @close="showSymlinkDialog = false"
      @created="onSymlinkCreated"
    />

    <!-- 子节点 (递归) -->
    <div v-if="item.is_dir && expanded">
      <div v-if="childLoading" class="flex items-center gap-1.5 py-0.5 text-gray-400" :style="{ paddingLeft: `${(depth + 1) * 16 + 4}px` }">
        <Loader2 :size="12" class="animate-spin" />
        <span class="text-[11px]">加载中...</span>
      </div>
      <div v-else-if="childError" class="text-red-400 text-[11px]" :style="{ paddingLeft: `${(depth + 1) * 16 + 4}px` }">
        {{ childError }}
      </div>
      <template v-else>
        <DirectoryTreeNode
          v-for="child in children"
          :key="child.path"
          :item="child"
          :depth="depth + 1"
        />
        <div
          v-if="children.length === 0 && !childLoading"
          class="text-gray-300 italic text-[11px] py-0.5"
          :style="{ paddingLeft: `${(depth + 1) * 16 + 4}px` }"
        >
          (空)
        </div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { listDir } from '@/api'
import type { ListDirItem } from '@/api'
import SymlinkDialog from '@/components/SymlinkDialog.vue'
import { ChevronRight, Folder, FolderOpen, File, Link, Loader2, Clipboard } from 'lucide-vue-next'

const props = defineProps<{
  item: ListDirItem
  depth: number
}>()

const expanded = ref(false)
const children = ref<ListDirItem[]>([])
const childLoading = ref(false)
const childError = ref('')
const loaded = ref(false)

// 右键菜单状态
const ctxMenu = ref({ show: false, x: 0, y: 0 })
const showSymlinkDialog = ref(false)

const symlinkTargetName = computed(() => {
  if (!props.item.symlink_target) return ''
  const parts = props.item.symlink_target.replace(/[\\/]+$/, '').split(/[\\/]/)
  return parts[parts.length - 1] || props.item.symlink_target
})

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`
}

function onContextMenu(e: MouseEvent) {
  ctxMenu.value = { show: true, x: e.clientX, y: e.clientY }
}

function closeCtxMenu() {
  ctxMenu.value.show = false
}

function handleCreateSymlink() {
  closeCtxMenu()
  showSymlinkDialog.value = true
}

function handleCopyPath() {
  closeCtxMenu()
  navigator.clipboard?.writeText(props.item.path)
}

function onSymlinkCreated() {
  // 刷新当前目录的父节点 — 简单方案：标记需要重新加载
  // 由于 symlink 可能创建在其他位置，这里不一定能刷新到
}

// 全局点击关闭菜单
function onGlobalClick() {
  if (ctxMenu.value.show) closeCtxMenu()
}

onMounted(() => {
  document.addEventListener('click', onGlobalClick)
})

onBeforeUnmount(() => {
  document.removeEventListener('click', onGlobalClick)
})

async function toggle() {
  if (!props.item.is_dir) return

  if (!expanded.value) {
    expanded.value = true
    if (!loaded.value) {
      childLoading.value = true
      childError.value = ''
      try {
        const { data } = await listDir(props.item.path)
        if (data.success) {
          children.value = data.items
        } else {
          childError.value = data.message || '无法加载'
        }
      } catch {
        childError.value = '加载失败'
      } finally {
        childLoading.value = false
        loaded.value = true
      }
    }
  } else {
    expanded.value = false
  }
}
</script>
