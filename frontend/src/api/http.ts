import axios from 'axios'
import type { AxiosInstance, InternalAxiosRequestConfig, AxiosResponse } from 'axios'
import { llmMonitor } from '@/composables/useLlmMonitor'

const http: AxiosInstance = axios.create({
  baseURL: '/api',
  timeout: 60_000,
  headers: { 'Content-Type': 'application/json' },
})

// ── LLM 请求拦截器 — 捕获所有 /api/llm/* 请求供 Debug Monitor 使用 ──

// 不需要捕获到 Monitor 的 LLM 管理/检测端点
const LLM_MONITOR_EXCLUDE = ['/llm/config', 'llm/config', '/llm/test-connection', 'llm/test-connection', '/llm/health', 'llm/health']

http.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const url = config.url ?? ''
  const isLlm = url.startsWith('/llm/') || url.startsWith('llm/')
  const isExcluded = LLM_MONITOR_EXCLUDE.some((p) => url.startsWith(p) || url === p)

  if (isLlm && !isExcluded) {
    const entry = llmMonitor.startRequest({
      method: config.method?.toUpperCase() ?? 'GET',
      url: config.url ?? '',
      body: config.data,
    })
    // 将 entry id 存入 config 供 response 拦截器关联
    ;(config as unknown as Record<string, unknown>)._llmEntryId = entry.id
  }
  return config
})

http.interceptors.response.use(
  (response: AxiosResponse) => {
    const entryId = (response.config as unknown as Record<string, unknown>)._llmEntryId as string | undefined
    if (entryId) {
      llmMonitor.endRequest(entryId, {
        status: response.status,
        data: response.data,
      })
    }
    return response
  },
  (error) => {
    const config = error.config as Record<string, unknown> | undefined
    const entryId = config?._llmEntryId as string | undefined
    if (entryId) {
      llmMonitor.endRequest(entryId, {
        status: error.response?.status ?? 0,
        data: error.response?.data ?? { error: error.message },
        isError: true,
      })
    }
    return Promise.reject(error)
  },
)

export default http
