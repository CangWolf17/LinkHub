<template>
  <transition name="slide-up">
    <div
      v-if="monitor.state.isOpen"
      ref="monitorEl"
      class="fixed z-50 flex flex-col text-sm bg-gray-900/95 backdrop-blur-sm rounded-xl shadow-2xl border border-gray-700"
      :style="monitorStyle"
    >
      <!-- 标题栏 (可拖拽) -->
      <div
        class="flex items-center justify-between px-4 py-2.5 border-b border-gray-700 cursor-move select-none"
        @mousedown.prevent="startDrag"
      >
        <div class="flex items-center gap-2">
          <span class="text-orange-400 text-xs font-bold tracking-wide uppercase">LLM Monitor</span>
          <span class="text-gray-500 text-xs">({{ monitor.state.entries.length }})</span>
        </div>
        <div class="flex items-center gap-1">
          <button
            class="text-gray-400 hover:text-gray-200 px-2 py-0.5 text-xs rounded hover:bg-gray-800 transition-colors"
            @click="monitor.clear()"
          >
            清空
          </button>
          <button
            class="text-gray-400 hover:text-gray-200 p-1 rounded hover:bg-gray-800 transition-colors"
            @click="monitor.toggle()"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>

      <!-- 日志列表 -->
      <div class="flex-1 overflow-y-auto">
        <div v-if="monitor.state.entries.length === 0" class="p-6 text-center text-gray-500 text-xs">
          暂无 LLM 请求记录。<br />所有 /api/llm/* 的请求会实时显示在这里。
        </div>

        <div
          v-for="entry in monitor.state.entries"
          :key="entry.id"
          class="border-b border-gray-800 px-4 py-3 hover:bg-gray-800/50 transition-colors"
        >
          <!-- 请求头 -->
          <div class="flex items-center gap-2 mb-1.5">
            <span
              class="px-1.5 py-0.5 rounded text-[10px] font-bold uppercase"
              :class="methodClass(entry.method)"
            >
              {{ entry.method }}
            </span>
            <span class="text-gray-300 text-xs font-mono truncate flex-1">{{ entry.url }}</span>
            <span v-if="entry.streaming && entry.pending" class="text-cyan-400 text-[10px] animate-pulse">streaming...</span>
            <span v-else-if="entry.pending" class="text-yellow-400 text-[10px] animate-pulse">pending...</span>
            <span v-else class="text-[10px]" :class="entry.isError ? 'text-red-400' : 'text-green-400'">
              {{ entry.responseStatus }} ({{ entry.duration }}ms)
            </span>
          </div>

          <!-- 流式输出实时显示 -->
          <div v-if="entry.streaming && entry.streamContent" class="mb-1.5">
            <div class="text-[10px] text-cyan-400 font-bold mb-0.5">Stream Output:</div>
            <pre class="text-[11px] text-gray-300 bg-gray-800 rounded p-2 overflow-x-auto max-h-40 whitespace-pre-wrap break-all">{{ entry.streamContent }}</pre>
          </div>

          <!-- 展开详情 -->
          <details class="group">
            <summary class="text-[10px] text-gray-500 cursor-pointer hover:text-gray-300 transition-colors">
              展开详情
            </summary>
            <div class="mt-2 space-y-2">
              <!-- Request Body -->
              <div v-if="entry.requestBody">
                <div class="text-[10px] text-blue-400 font-bold mb-0.5">User Prompt:</div>
                <pre class="text-[11px] text-gray-300 bg-gray-800 rounded p-2 overflow-x-auto max-h-32 whitespace-pre-wrap break-all">{{ formatBody(entry.requestBody) }}</pre>
              </div>
              <!-- Response -->
              <div v-if="entry.responseData && !entry.streaming">
                <div class="text-[10px] font-bold mb-0.5" :class="entry.isError ? 'text-red-400' : 'text-green-400'">
                  LLM Raw Output:
                </div>
                <pre class="text-[11px] text-gray-300 bg-gray-800 rounded p-2 overflow-x-auto max-h-40 whitespace-pre-wrap break-all">{{ formatBody(entry.responseData) }}</pre>
              </div>
            </div>
          </details>
        </div>
      </div>

      <!-- 右下角 resize 手柄 -->
      <div
        class="absolute bottom-0 right-0 w-4 h-4 cursor-nwse-resize"
        @mousedown.prevent="startResize"
      >
        <svg class="w-3 h-3 text-gray-600 absolute bottom-0.5 right-0.5" viewBox="0 0 10 10" fill="currentColor">
          <path d="M9 1v8H1" fill="none" stroke="currentColor" stroke-width="1.5" />
          <path d="M9 5v4H5" fill="none" stroke="currentColor" stroke-width="1.5" />
        </svg>
      </div>
    </div>
  </transition>
</template>

<script setup lang="ts">
import { ref, computed, onBeforeUnmount } from 'vue'
import { useLlmMonitor } from '@/composables/useLlmMonitor'

const monitor = useLlmMonitor()
const monitorEl = ref<HTMLElement | null>(null)

// ── 位置 & 尺寸状态 ────────────────────────────────
const posX = ref<number | null>(null)
const posY = ref<number | null>(null)
const width = ref(480)
const height = ref(420)

const monitorStyle = computed(() => {
  const styles: Record<string, string> = {
    width: `${width.value}px`,
    maxHeight: `${height.value}px`,
  }
  if (posX.value !== null && posY.value !== null) {
    styles.left = `${posX.value}px`
    styles.top = `${posY.value}px`
  } else {
    styles.bottom = '16px'
    styles.right = '16px'
  }
  return styles
})

// ── 拖拽 ────────────────────────────────────────────
let dragging = false
let dragOffsetX = 0
let dragOffsetY = 0

function startDrag(e: MouseEvent) {
  dragging = true
  const el = monitorEl.value
  if (!el) return
  const rect = el.getBoundingClientRect()
  // 如果还没设置过绝对位置，先初始化
  if (posX.value === null) {
    posX.value = rect.left
    posY.value = rect.top
  }
  dragOffsetX = e.clientX - rect.left
  dragOffsetY = e.clientY - rect.top
  document.addEventListener('mousemove', onDragMove)
  document.addEventListener('mouseup', onDragEnd)
}

function onDragMove(e: MouseEvent) {
  if (!dragging) return
  posX.value = Math.max(0, e.clientX - dragOffsetX)
  posY.value = Math.max(0, e.clientY - dragOffsetY)
}

function onDragEnd() {
  dragging = false
  document.removeEventListener('mousemove', onDragMove)
  document.removeEventListener('mouseup', onDragEnd)
}

// ── 调节大小 ────────────────────────────────────────
let resizing = false
let resizeStartX = 0
let resizeStartY = 0
let resizeStartW = 0
let resizeStartH = 0

function startResize(e: MouseEvent) {
  resizing = true
  resizeStartX = e.clientX
  resizeStartY = e.clientY
  resizeStartW = width.value
  resizeStartH = height.value
  document.addEventListener('mousemove', onResizeMove)
  document.addEventListener('mouseup', onResizeEnd)
}

function onResizeMove(e: MouseEvent) {
  if (!resizing) return
  width.value = Math.max(320, resizeStartW + (e.clientX - resizeStartX))
  height.value = Math.max(200, resizeStartH + (e.clientY - resizeStartY))
}

function onResizeEnd() {
  resizing = false
  document.removeEventListener('mousemove', onResizeMove)
  document.removeEventListener('mouseup', onResizeEnd)
}

// ── helpers ─────────────────────────────────────────

function methodClass(method: string): string {
  switch (method) {
    case 'POST': return 'bg-green-900 text-green-300'
    case 'PUT': return 'bg-yellow-900 text-yellow-300'
    case 'GET': return 'bg-blue-900 text-blue-300'
    case 'DELETE': return 'bg-red-900 text-red-300'
    default: return 'bg-gray-700 text-gray-300'
  }
}

function formatBody(data: unknown): string {
  if (typeof data === 'string') return data
  try {
    return JSON.stringify(data, null, 2)
  } catch {
    return String(data)
  }
}

onBeforeUnmount(() => {
  document.removeEventListener('mousemove', onDragMove)
  document.removeEventListener('mouseup', onDragEnd)
  document.removeEventListener('mousemove', onResizeMove)
  document.removeEventListener('mouseup', onResizeEnd)
})
</script>
