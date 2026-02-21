/**
 * LLM Debug Monitor — 全局状态管理
 * 拦截并记录所有 /api/llm/* 的请求和响应。
 * 前端 LLM Debug 悬浮窗读取此数据。
 */
import { reactive } from 'vue'

export interface LlmLogEntry {
  id: string
  timestamp: number
  method: string
  url: string
  requestBody: unknown
  responseStatus: number | null
  responseData: unknown
  isError: boolean
  duration: number | null  // ms
  pending: boolean
}

interface LlmMonitorState {
  entries: LlmLogEntry[]
  isOpen: boolean
}

const state = reactive<LlmMonitorState>({
  entries: [],
  isOpen: false,
})

let _nextId = 1

function startRequest(info: { method: string; url: string; body: unknown }): LlmLogEntry {
  const entry: LlmLogEntry = {
    id: `llm-${_nextId++}`,
    timestamp: Date.now(),
    method: info.method,
    url: info.url,
    requestBody: info.body,
    responseStatus: null,
    responseData: null,
    isError: false,
    duration: null,
    pending: true,
  }
  state.entries.unshift(entry)
  // 最多保留 50 条
  if (state.entries.length > 50) {
    state.entries.length = 50
  }
  return entry
}

function endRequest(
  entryId: string,
  result: { status: number; data: unknown; isError?: boolean },
) {
  const entry = state.entries.find((e) => e.id === entryId)
  if (entry) {
    entry.responseStatus = result.status
    entry.responseData = result.data
    entry.isError = result.isError ?? false
    entry.duration = Date.now() - entry.timestamp
    entry.pending = false
  }
}

function clear() {
  state.entries.length = 0
}

function toggle() {
  state.isOpen = !state.isOpen
}

export const llmMonitor = {
  state,
  startRequest,
  endRequest,
  clear,
  toggle,
}

export function useLlmMonitor() {
  return llmMonitor
}
