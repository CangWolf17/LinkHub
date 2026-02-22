<template>
  <div class="h-full flex flex-col">
    <div class="flex items-center justify-between mb-4">
      <h1 class="text-2xl font-bold text-gray-900">系统日志</h1>
      <div class="flex items-center gap-2">
        <!-- 级别过滤 -->
        <select
          v-model="levelFilter"
          class="px-2 py-1.5 text-xs border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
        >
          <option value="">全部级别</option>
          <option value="ERROR">ERROR</option>
          <option value="WARNING">WARNING</option>
          <option value="INFO">INFO</option>
          <option value="DEBUG">DEBUG</option>
        </select>
        <!-- 搜索 -->
        <input
          v-model="searchQuery"
          type="text"
          placeholder="搜索日志..."
          class="px-3 py-1.5 text-xs border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 w-48"
        />
        <!-- 连接状态 -->
        <div class="flex items-center gap-1.5 text-xs text-gray-500">
          <span
            class="w-2 h-2 rounded-full"
            :class="wsConnected ? 'bg-green-400' : 'bg-red-400'"
          />
          {{ wsConnected ? '实时' : '离线' }}
        </div>
        <!-- 自动滚动 -->
        <button
          class="px-2 py-1.5 text-xs rounded-lg transition-colors"
          :class="autoScroll
            ? 'bg-blue-50 text-blue-600 hover:bg-blue-100'
            : 'bg-gray-100 text-gray-500 hover:bg-gray-200'"
          @click="autoScroll = !autoScroll"
        >
          {{ autoScroll ? '自动滚动: 开' : '自动滚动: 关' }}
        </button>
        <!-- 清空 -->
        <button
          class="px-2 py-1.5 text-xs text-gray-500 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
          @click="logs = []"
        >
          清空
        </button>
      </div>
    </div>

    <!-- 日志列表 -->
    <div
      ref="logContainer"
      class="flex-1 min-h-0 overflow-y-auto bg-gray-900 rounded-xl p-3 font-mono text-xs leading-relaxed"
      @scroll="onScroll"
    >
      <div v-if="filteredLogs.length === 0" class="text-gray-500 text-center py-8">
        暂无日志
      </div>
      <div
        v-for="log in filteredLogs"
        :key="log.id"
        class="flex gap-2 py-0.5 hover:bg-gray-800/50 px-1 rounded"
      >
        <span class="text-gray-500 shrink-0 w-20">{{ formatTime(log.timestamp) }}</span>
        <span
          class="shrink-0 w-16 text-center font-semibold"
          :class="levelColor(log.level)"
        >{{ log.level }}</span>
        <span class="text-gray-400 shrink-0 w-28 truncate" :title="log.logger">{{ log.logger }}</span>
        <span class="text-gray-200 break-all">{{ log.message }}</span>
      </div>
    </div>

    <!-- 底部统计 -->
    <div class="flex items-center justify-between mt-2 text-xs text-gray-400">
      <span>显示 {{ filteredLogs.length }} / {{ logs.length }} 条</span>
      <span v-if="logs.length > 0">最新: {{ logs[logs.length - 1]?.timestamp }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { getLogs } from '@/api'

interface LogEntry {
  id: number
  timestamp: string
  level: string
  logger: string
  message: string
}

const logs = ref<LogEntry[]>([])
const levelFilter = ref('')
const searchQuery = ref('')
const autoScroll = ref(true)
const wsConnected = ref(false)
const logContainer = ref<HTMLElement | null>(null)

let ws: WebSocket | null = null
let reconnectTimer: ReturnType<typeof setTimeout> | null = null

const filteredLogs = computed(() => {
  let result = logs.value
  if (levelFilter.value) {
    result = result.filter(l => l.level === levelFilter.value)
  }
  if (searchQuery.value.trim()) {
    const q = searchQuery.value.toLowerCase()
    result = result.filter(l =>
      l.message.toLowerCase().includes(q) ||
      l.logger.toLowerCase().includes(q)
    )
  }
  return result
})

function formatTime(ts: string): string {
  if (!ts) return ''
  // timestamp 格式: 2026-02-22T12:34:56.789
  const parts = ts.split('T')
  return parts.length > 1 ? parts[1] : ts
}

function levelColor(level: string): string {
  switch (level) {
    case 'ERROR': return 'text-red-400'
    case 'WARNING': return 'text-yellow-400'
    case 'INFO': return 'text-green-400'
    case 'DEBUG': return 'text-gray-400'
    default: return 'text-gray-400'
  }
}

function scrollToBottom() {
  if (autoScroll.value && logContainer.value) {
    nextTick(() => {
      if (logContainer.value) {
        logContainer.value.scrollTop = logContainer.value.scrollHeight
      }
    })
  }
}

function onScroll() {
  if (!logContainer.value) return
  const el = logContainer.value
  const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 40
  autoScroll.value = atBottom
}

// 添加日志条目（去重 + 限制总量）
function addLog(entry: LogEntry) {
  logs.value.push(entry)
  // 限制内存中保留 2000 条
  if (logs.value.length > 2000) {
    logs.value = logs.value.slice(-1500)
  }
  scrollToBottom()
}

// WebSocket 连接
function connectWs() {
  if (ws) {
    ws.close()
    ws = null
  }

  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const wsUrl = `${protocol}//${window.location.host}/api/ws/logs`
  ws = new WebSocket(wsUrl)

  ws.onopen = () => {
    wsConnected.value = true
  }

  ws.onmessage = (event) => {
    try {
      const entry: LogEntry = JSON.parse(event.data)
      addLog(entry)
    } catch { /* ignore parse errors */ }
  }

  ws.onclose = () => {
    wsConnected.value = false
    // 自动重连
    reconnectTimer = setTimeout(connectWs, 3000)
  }

  ws.onerror = () => {
    wsConnected.value = false
  }
}

// 初始加载历史日志
async function loadHistory() {
  try {
    const { data } = await getLogs(300)
    logs.value = data.logs
    scrollToBottom()
  } catch { /* ignore */ }
}

watch(filteredLogs, () => {
  scrollToBottom()
})

onMounted(async () => {
  await loadHistory()
  connectWs()
})

onUnmounted(() => {
  if (reconnectTimer) clearTimeout(reconnectTimer)
  if (ws) {
    ws.onclose = null
    ws.close()
  }
})
</script>
