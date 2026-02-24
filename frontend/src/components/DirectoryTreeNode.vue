<template>
  <div>
    <!-- 当前条目 -->
    <div
      class="flex items-center gap-1.5 py-0.5 px-1 rounded hover:bg-gray-50 cursor-default select-none group"
      :style="{ paddingLeft: `${depth * 16 + 4}px` }"
      @click="toggle"
      @contextmenu="openCtxMenu"
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
          <span v-if="item.is_symlink || item.link_type" class="inline-flex items-center gap-0.5 text-purple-500" :title="linkTooltip"><Link :size="12" /><Folder :size="12" /></span>
          <FolderOpen v-else-if="expanded" :size="12" class="text-yellow-500" />
          <Folder v-else :size="12" class="text-yellow-600" />
        </template>
        <template v-else>
          <span v-if="item.is_symlink || item.link_type" class="text-purple-500" :title="linkTooltip"><Link :size="12" /></span>
          <File v-else :size="12" class="text-gray-400" />
        </template>
      </span>

      <!-- 名称 -->
      <span
        class="truncate"
        :class="[
          item.is_dir ? 'text-gray-700 font-medium' : 'text-gray-500',
          (item.is_symlink || item.link_type) ? 'italic' : '',
        ]"
        :title="item.path + (item.symlink_target ? ` → ${item.symlink_target}` : '')"
      >
        {{ item.name }}
      </span>

      <!-- 符号链接标记 -->
      <span v-if="item.is_symlink || item.link_type" class="text-[10px] text-purple-400 flex-shrink-0 ml-1">
        <template v-if="item.link_type === 'lnk'">[快捷方式]</template>
        <template v-else-if="item.link_type === 'junction'">[junction]</template>
        <template v-else>&#8594; {{ symlinkTargetName }}</template>
      </span>

      <!-- 文件大小 -->
      <span v-if="!item.is_dir && item.size !== null" class="text-[10px] text-gray-300 ml-auto flex-shrink-0">
        {{ formatSize(item.size) }}
      </span>
    </div>

    <!-- 右键菜单（使用共享 ContextMenu 组件） -->
    <ContextMenu ref="ctxMenuRef" :items="ctxMenuItems" />

    <!-- 符号链接弹窗 -->
    <SymlinkDialog
      v-if="showSymlinkDialog"
      :target-dir="item.path"
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
import { ref, computed } from 'vue'
import { listDir } from '@/api'
import type { ListDirItem } from '@/api'
import ContextMenu from '@/components/ContextMenu.vue'
import type { ContextMenuItem } from '@/components/ContextMenu.vue'
import SymlinkDialog from '@/components/SymlinkDialog.vue'
import { ChevronRight, Folder, FolderOpen, File, Link, Loader2, Clipboard, ExternalLink } from 'lucide-vue-next'

const props = defineProps<{
  item: ListDirItem
  depth: number
}>()

const expanded = ref(false)
const children = ref<ListDirItem[]>([])
const childLoading = ref(false)
const childError = ref('')
const loaded = ref(false)

// 共享 ContextMenu
const ctxMenuRef = ref<InstanceType<typeof ContextMenu> | null>(null)
const showSymlinkDialog = ref(false)

const symlinkTargetName = computed(() => {
  if (!props.item.symlink_target) return ''
  const parts = props.item.symlink_target.replace(/[\\/]+$/, '').split(/[\\/]/)
  return parts[parts.length - 1] || props.item.symlink_target
})

const linkTooltip = computed(() => {
  const lt = props.item.link_type
  if (lt === 'lnk') return `快捷方式 → ${props.item.symlink_target || '未知'}`
  if (lt === 'junction') return `目录联接 → ${props.item.symlink_target || '未知'}`
  return props.item.is_symlink ? `符号链接${props.item.is_dir ? '目录' : '文件'}` : ''
})

const ctxMenuItems = computed<ContextMenuItem[]>(() => {
  const items: ContextMenuItem[] = []

  // 创建目录映射（仅非链接的目录）
  if (props.item.is_dir && !props.item.is_symlink && !props.item.link_type) {
    items.push({
      label: '创建目录映射',
      icon: Link,
      action: () => { showSymlinkDialog.value = true },
    })
  }

  // 复制路径
  items.push({
    label: '复制路径',
    icon: Clipboard,
    action: () => navigator.clipboard?.writeText(props.item.path),
  })

  // 链接相关：定位到源路径
  if ((props.item.is_symlink || props.item.link_type) && props.item.symlink_target) {
    items.push({ separator: true })
    items.push({
      label: '在资源管理器中打开源路径',
      icon: ExternalLink,
      action: () => {
        // 打开源路径所在目录
        const target = props.item.symlink_target!
        const folder = target.replace(/[\\/][^\\/]+$/, '')
        window.open(`file:///${folder.replace(/\\/g, '/')}`, '_blank')
      },
    })
  }

  return items
})

function openCtxMenu(e: MouseEvent) {
  ctxMenuRef.value?.open(e)
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`
}

function onSymlinkCreated() {
  // 刷新当前目录的父节点 — 简单方案：标记需要重新加载
  // 由于 symlink 可能创建在其他位置，这里不一定能刷新到
}

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
