/**
 * LLM Debug Monitor — 全局状态管理
 * 拦截并记录所有 /api/llm/* 的请求和响应。
 * 前端 LLM Debug 悬浮窗读取此数据。
 * 支持流式 (SSE) 和非流式两种模式。
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
  // 流式输出相关
  streaming: boolean
  streamContent: string
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
    streaming: false,
    streamContent: '',
  }
  state.entries.unshift(entry)
  // 最多保留 50 条
  if (state.entries.length > 50) {
    state.entries.length = 50
  }
  return entry
}

/** 开始一个流式请求（手动创建 entry，不走 axios 拦截器） */
function startStreamRequest(info: { url: string; body: unknown }): LlmLogEntry {
  const entry: LlmLogEntry = {
    id: `llm-${_nextId++}`,
    timestamp: Date.now(),
    method: 'POST',
    url: info.url,
    requestBody: info.body,
    responseStatus: null,
    responseData: null,
    isError: false,
    duration: null,
    pending: true,
    streaming: true,
    streamContent: '',
  }
  state.entries.unshift(entry)
  if (state.entries.length > 50) {
    state.entries.length = 50
  }
  return entry
}

/** 追加流式增量文本 */
function appendStreamDelta(entryId: string, delta: string) {
  const entry = state.entries.find((e) => e.id === entryId)
  if (entry) {
    entry.streamContent += delta
  }
}

/** 结束流式请求 */
function endStreamRequest(
  entryId: string,
  result: { content?: string; error?: string },
) {
  const entry = state.entries.find((e) => e.id === entryId)
  if (entry) {
    entry.responseStatus = result.error ? 500 : 200
    entry.responseData = result.error || result.content || entry.streamContent
    entry.isError = !!result.error
    entry.duration = Date.now() - entry.timestamp
    entry.pending = false
  }
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
  startStreamRequest,
  appendStreamDelta,
  endStreamRequest,
  endRequest,
  clear,
  toggle,
}

export function useLlmMonitor() {
  return llmMonitor
}
