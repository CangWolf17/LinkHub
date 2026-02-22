<template>
  <Teleport to="body">
    <div
      class="fixed inset-0 z-[60] flex items-center justify-center bg-black/40"
      @click.self="$emit('cancel')"
    >
      <div class="bg-white rounded-xl shadow-xl w-full max-w-lg mx-4 flex flex-col" style="max-height: 70vh">
        <!-- 标题 -->
        <div class="flex items-center justify-between px-5 py-3 border-b border-gray-200">
          <h3 class="text-sm font-bold text-gray-900">选择文件夹</h3>
          <button
            class="p-1 text-gray-400 hover:text-gray-600 transition-colors"
            @click="$emit('cancel')"
          >
            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <!-- 当前路径面包屑 -->
        <div class="px-5 py-2 border-b border-gray-100 bg-gray-50">
          <div class="flex items-center gap-1 text-xs text-gray-500 overflow-x-auto whitespace-nowrap">
            <button
              class="hover:text-blue-600 font-medium shrink-0"
              @click="navigateTo('')"
            >
              此电脑
            </button>
            <template v-for="(seg, i) in breadcrumbs" :key="i">
              <span class="text-gray-300">/</span>
              <button
                class="hover:text-blue-600 shrink-0"
                @click="navigateTo(seg.path)"
              >
                {{ seg.name }}
              </button>
            </template>
          </div>
        </div>

        <!-- 目录列表 -->
        <div class="flex-1 overflow-y-auto min-h-0 px-2 py-1">
          <div v-if="loading" class="flex items-center justify-center py-8 text-sm text-gray-400">
            加载中...
          </div>
          <div v-else-if="error" class="flex items-center justify-center py-8 text-sm text-red-500">
            {{ error }}
          </div>
          <div v-else-if="items.length === 0" class="flex items-center justify-center py-8 text-sm text-gray-400">
            此目录为空
          </div>
          <div v-else class="space-y-px">
            <!-- 返回上级 -->
            <button
              v-if="parentPath !== undefined"
              class="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
              @click="navigateTo(parentPath || '')"
            >
              <svg class="w-4 h-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 17l-5-5m0 0l5-5m-5 5h12" />
              </svg>
              <span class="text-gray-500">返回上级</span>
            </button>
            <!-- 子目录列表 -->
            <button
              v-for="item in items"
              :key="item.path"
              class="w-full flex items-center gap-2 px-3 py-2 text-sm rounded-lg transition-colors"
              :class="selectedPath === item.path
                ? 'bg-blue-50 text-blue-700'
                : 'text-gray-700 hover:bg-gray-100'"
              @click="selectItem(item)"
              @dblclick="navigateTo(item.path)"
            >
              <svg class="w-4 h-4 text-yellow-500 shrink-0" fill="currentColor" viewBox="0 0 20 20">
                <path d="M2 6a2 2 0 012-2h5l2 2h5a2 2 0 012 2v6a2 2 0 01-2 2H4a2 2 0 01-2-2V6z" />
              </svg>
              <span class="truncate">{{ item.name }}</span>
            </button>
          </div>
        </div>

        <!-- 选中路径 + 按钮 -->
        <div class="px-5 py-3 border-t border-gray-200 bg-gray-50 space-y-2">
          <div class="flex items-center gap-2">
            <span class="text-xs text-gray-500 shrink-0">已选:</span>
            <input
              v-model="manualInput"
              type="text"
              placeholder="选择或输入目录路径..."
              class="flex-1 px-2 py-1 text-xs border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500 font-mono"
              @keydown.enter="confirmSelection"
            />
          </div>
          <div class="flex justify-end gap-2">
            <button
              class="px-3 py-1.5 text-xs font-medium text-gray-600 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
              @click="$emit('cancel')"
            >
              取消
            </button>
            <button
              class="px-3 py-1.5 text-xs font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
              :disabled="!manualInput.trim()"
              @click="confirmSelection"
            >
              确定
            </button>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { browseDir } from '@/api'
import type { DirItem } from '@/api'

const props = defineProps<{
  initialPath?: string
}>()

const emit = defineEmits<{
  confirm: [path: string]
  cancel: []
}>()

const loading = ref(false)
const error = ref('')
const currentPath = ref('')
const parentPath = ref<string | null | undefined>(undefined)
const items = ref<DirItem[]>([])
const selectedPath = ref('')
const manualInput = ref(props.initialPath || '')

// 面包屑计算
const breadcrumbs = computed(() => {
  if (!currentPath.value) return []
  const parts: { name: string; path: string }[] = []
  const p = currentPath.value.replace(/\\/g, '/')
  const segments = p.split('/').filter(Boolean)
  let accumulated = ''
  for (const seg of segments) {
    accumulated += (accumulated && !accumulated.endsWith('/') ? '/' : '') + seg
    // Windows: 对首个 segment（如 C:），补上反斜杠
    const displayPath = parts.length === 0 && seg.endsWith(':') ? seg + '\\' : accumulated
    parts.push({ name: seg, path: displayPath })
  }
  return parts
})

async function navigateTo(path: string) {
  loading.value = true
  error.value = ''
  try {
    const { data } = await browseDir(path || undefined)
    currentPath.value = data.current
    parentPath.value = data.parent
    items.value = data.items
    // 更新手动输入框为当前目录
    if (data.current) {
      manualInput.value = data.current
      selectedPath.value = data.current
    }
  } catch (e: unknown) {
    const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '加载目录失败'
    error.value = typeof detail === 'string' ? detail : JSON.stringify(detail)
  } finally {
    loading.value = false
  }
}

function selectItem(item: DirItem) {
  selectedPath.value = item.path
  manualInput.value = item.path
}

function confirmSelection() {
  const path = manualInput.value.trim()
  if (path) {
    emit('confirm', path)
  }
}

// 监听 selectedPath 同步到手动输入
watch(selectedPath, (val) => {
  if (val) manualInput.value = val
})

onMounted(() => {
  // 如果有初始路径，先导航到其父目录
  if (props.initialPath) {
    const p = props.initialPath.replace(/\\/g, '/')
    const lastSlash = p.lastIndexOf('/')
    const parent = lastSlash > 0 ? p.substring(0, lastSlash) : ''
    navigateTo(parent || props.initialPath)
  } else {
    navigateTo('')
  }
})
</script>
