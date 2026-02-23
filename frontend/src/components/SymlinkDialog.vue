<template>
  <!-- 弹窗遮罩 -->
  <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/40" @click.self="$emit('close')">
    <div class="bg-white rounded-xl shadow-xl w-full max-w-lg mx-4 p-6">
      <h3 class="text-lg font-bold text-gray-900 mb-4">创建目录链接</h3>

      <div class="space-y-4">
        <!-- 源目录 (只读) -->
        <div>
          <label class="block text-xs font-medium text-gray-500 mb-1">源目录（链接指向）</label>
          <div
            class="flex items-center gap-2 px-3 py-2 text-sm bg-gray-50 border border-gray-200 rounded-lg font-mono text-gray-700"
            :title="sourcePath"
          >
            <svg class="w-4 h-4 text-yellow-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
            </svg>
            <span class="truncate">{{ sourcePath }}</span>
          </div>
        </div>

        <!-- 动画连接线 -->
        <div class="flex justify-center py-1">
          <div class="flex flex-col items-center gap-1">
            <svg class="w-5 h-5 text-purple-400 animate-bounce" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 14l-7 7m0 0l-7-7m7 7V3" />
            </svg>
            <span class="text-[10px] text-purple-400 font-medium">JUNCTION</span>
          </div>
        </div>

        <!-- 目标位置：选择链接要创建在哪个目录下 -->
        <div>
          <label class="block text-xs font-medium text-gray-500 mb-1">链接位置（创建在哪里）</label>
          <div class="flex items-center gap-2">
            <input
              v-model="targetDir"
              type="text"
              placeholder="选择目标目录"
              class="flex-1 px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent font-mono"
            />
            <button
              type="button"
              class="p-2 text-gray-400 hover:text-purple-500 transition-colors shrink-0"
              title="浏览..."
              @click="showBrowser = true"
            >
              <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
              </svg>
            </button>
          </div>
        </div>

        <!-- 链接名称 -->
        <div>
          <label class="block text-xs font-medium text-gray-500 mb-1">链接名称</label>
          <input
            v-model="linkName"
            type="text"
            placeholder="留空则使用源目录名"
            class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent"
          />
        </div>

        <!-- 预览 -->
        <div v-if="fullLinkPath" class="bg-purple-50 rounded-lg px-3 py-2">
          <div class="text-[10px] text-purple-500 font-medium mb-1">将创建链接:</div>
          <div class="text-xs font-mono text-purple-700 truncate" :title="fullLinkPath">
            {{ fullLinkPath }}
          </div>
          <div class="text-[10px] text-purple-400 mt-0.5">
            &#8594; {{ sourcePath }}
          </div>
        </div>
      </div>

      <!-- 错误消息 -->
      <div v-if="error" class="mt-3 p-2 text-xs text-red-600 bg-red-50 rounded-lg">{{ error }}</div>

      <!-- 成功消息 -->
      <div v-if="successMsg" class="mt-3 p-2 text-xs text-green-600 bg-green-50 rounded-lg">{{ successMsg }}</div>

      <!-- 按钮 -->
      <div class="flex items-center justify-end gap-3 mt-5">
        <button
          class="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
          @click="$emit('close')"
        >
          {{ successMsg ? '关闭' : '取消' }}
        </button>
        <button
          v-if="!successMsg"
          class="px-4 py-2 text-sm font-medium text-white bg-purple-600 rounded-lg hover:bg-purple-700 disabled:opacity-50 transition-colors"
          :disabled="creating || !fullLinkPath"
          @click="doCreate"
        >
          {{ creating ? '创建中...' : '创建链接' }}
        </button>
      </div>
    </div>
  </div>

  <!-- 文件夹浏览器 -->
  <FolderPickerDialog
    v-if="showBrowser"
    :initial-path="targetDir"
    @confirm="onFolderPicked"
    @cancel="showBrowser = false"
  />
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { createSymlink } from '@/api'
import FolderPickerDialog from '@/components/FolderPickerDialog.vue'

const props = defineProps<{
  sourcePath: string
}>()

const emit = defineEmits<{
  close: []
  created: []
}>()

const targetDir = ref('')
const linkName = ref('')
const creating = ref(false)
const error = ref('')
const successMsg = ref('')
const showBrowser = ref(false)

// 从源路径中提取默认名称
const defaultName = computed(() => {
  const parts = props.sourcePath.replace(/[\\/]+$/, '').split(/[\\/]/)
  return parts[parts.length - 1] || ''
})

const fullLinkPath = computed(() => {
  if (!targetDir.value.trim()) return ''
  const name = linkName.value.trim() || defaultName.value
  if (!name) return ''
  const sep = targetDir.value.includes('/') ? '/' : '\\'
  return targetDir.value.replace(/[\\/]+$/, '') + sep + name
})

function onFolderPicked(path: string) {
  targetDir.value = path
  showBrowser.value = false
}

async function doCreate() {
  if (!fullLinkPath.value || creating.value) return

  creating.value = true
  error.value = ''
  successMsg.value = ''

  try {
    const { data } = await createSymlink(props.sourcePath, fullLinkPath.value)
    if (data.success) {
      successMsg.value = `链接已创建: ${data.link_path}`
      emit('created')
    } else {
      error.value = data.message || '创建失败'
    }
  } catch (e: unknown) {
    const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '创建链接失败'
    error.value = typeof detail === 'string' ? detail : JSON.stringify(detail)
  } finally {
    creating.value = false
  }
}
</script>
