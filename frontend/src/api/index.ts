/**
 * API 模块：统一封装所有后端接口调用
 */
import http from './http'

// ── Types ────────────────────────────────────────────────

export interface Software {
  id: string
  name: string
  executable_path: string
  description: string | null
  tags: string | null
  icon_path: string | null
  is_missing?: boolean
  created_at: string
  updated_at: string
}

export interface Workspace {
  id: string
  name: string
  directory_path: string
  description: string | null
  deadline: string | null
  status: string
  is_missing?: boolean
  created_at: string
  updated_at: string
}

export interface LlmConfig {
  llm_base_url: string
  llm_api_key: string
  has_api_key: boolean
  model_chat: string
  model_embedding: string
  llm_system_prompt_software: string
  llm_system_prompt_workspace: string
}

export interface SearchResultItem {
  id: string
  name: string
  type: string
  description: string | null
  path: string
  score: number
  is_missing: boolean
}

export interface SearchResponse {
  success: boolean
  results: SearchResultItem[]
  total: number
  query: string
}

export interface DirEntry {
  path: string
  type: 'software' | 'workspace'
}

export interface DirItem {
  name: string
  path: string
  is_dir: boolean
}

export interface BrowseDirResponse {
  current: string
  parent: string | null
  items: DirItem[]
}

export interface InstallerUploadResponse {
  success: boolean
  software_id: string
  name: string
  executable_path: string
  install_dir: string
  description: string
  exe_candidates: string[]
  message: string
}

export interface ScanDirsResponse {
  success: boolean
  imported: number
  skipped: number
  failed: number
  details: Array<{ name: string; status: string; reason?: string; executable_path?: string; description?: string }>
  message: string
}

export interface WorkspaceScanResponse {
  success: boolean
  imported: number
  skipped: number
  details: Array<{ name: string; status: string; reason?: string; path?: string }>
  message: string
}

export interface IndexStats {
  software_count: number
  workspace_count: number
}

// ── Health ───────────────────────────────────────────────

export const getHealth = () => http.get<{ status: string }>('/health')

// ── System ───────────────────────────────────────────────

export const getInitStatus = () =>
  http.get<{
    needs_setup: boolean
    allowed_dirs: DirEntry[]
    llm_configured: boolean
  }>('/system/init-status')

export const getAllowedDirs = () =>
  http.get<{ allowed_dirs: DirEntry[] }>('/system/allowed-dirs')

export const updateAllowedDirs = (dirs: DirEntry[]) =>
  http.put<{ allowed_dirs: DirEntry[] }>('/system/allowed-dirs', { allowed_dirs: dirs })

// ── Software (Module B) ─────────────────────────────────

export const getSoftwareList = (params?: { search?: string }) =>
  http.get<{ items: Software[]; total: number }>('/metadata/software', { params })

export const getSoftware = (id: string) =>
  http.get<Software>(`/metadata/software/${id}`)

export const createSoftware = (data: Partial<Software>) =>
  http.post<Software>('/metadata/software', data)

export const updateSoftware = (id: string, data: Partial<Software>) =>
  http.put<Software>(`/metadata/software/${id}`, data)

export const deleteSoftware = (id: string) =>
  http.delete(`/metadata/software/${id}`)

export const cleanupDeadSoftware = () =>
  http.delete<{ removed_count: number }>('/metadata/software/cleanup/dead-links')

export const batchDeleteSoftware = (ids: string[]) =>
  http.post<{ deleted_count: number; deleted: Array<{ id: string; name: string }> }>(
    '/metadata/software/batch-delete',
    { ids }
  )

export const generateSoftwareDescription = (id: string, customPrompt?: string, mode?: 'append' | 'override') =>
  http.post<{ success: boolean; description: string; model: string; message: string }>(
    `/metadata/software/${id}/generate-description`,
    customPrompt ? { custom_prompt: customPrompt, mode: mode || 'append' } : {}
  )

// ── Workspaces (Module B) ────────────────────────────────

export const getWorkspaceList = (params?: { search?: string; status?: string }) =>
  http.get<{ items: Workspace[]; total: number }>('/metadata/workspaces', { params })

export const getWorkspace = (id: string) =>
  http.get<Workspace>(`/metadata/workspaces/${id}`)

export const createWorkspace = (data: Partial<Workspace>) =>
  http.post<Workspace>('/metadata/workspaces', data)

export const updateWorkspace = (id: string, data: Partial<Workspace>) =>
  http.put<Workspace>(`/metadata/workspaces/${id}`, data)

export const deleteWorkspace = (id: string) =>
  http.delete(`/metadata/workspaces/${id}`)

export const cleanupDeadWorkspaces = () =>
  http.delete<{ removed_count: number }>('/metadata/workspaces/cleanup/dead-links')

export const batchDeleteWorkspaces = (ids: string[]) =>
  http.post<{ deleted_count: number; deleted: Array<{ id: string; name: string }> }>(
    '/metadata/workspaces/batch-delete',
    { ids }
  )

export const batchUpdateWorkspaceStatus = (ids: string[], status: string) =>
  http.post<{ updated_count: number; status: string; updated: Array<{ id: string; name: string }> }>(
    '/metadata/workspaces/batch-update-status',
    { ids, status }
  )

export const generateWorkspaceDescription = (id: string, customPrompt?: string, mode?: 'append' | 'override') =>
  http.post<{ success: boolean; description: string; model: string; message: string }>(
    `/metadata/workspaces/${id}/generate-description`,
    customPrompt ? { custom_prompt: customPrompt, mode: mode || 'append' } : {}
  )

// ── LLM Gateway (Module C) ──────────────────────────────

export const getLlmConfig = () =>
  http.get<LlmConfig>('/llm/config')

export const updateLlmConfig = (data: Partial<LlmConfig>) =>
  http.put<LlmConfig>('/llm/config', data)

export const testLlmConnection = () =>
  http.post<{ success: boolean; message: string; model: string; raw_response: unknown }>('/llm/test-connection')

export const llmChat = (messages: Array<{ role: string; content: string }>) =>
  http.post('/llm/chat', { messages })

// ── Installer (Module D) ────────────────────────────────

export const uploadInstall = (file: File) => {
  const form = new FormData()
  form.append('file', file)
  return http.post<InstallerUploadResponse>('/installer/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 300_000,
  })
}

export const scanAndImportSoftware = () =>
  http.post<ScanDirsResponse>('/installer/scan-dirs', null, { timeout: 300_000 })

export const scanAndImportWorkspaces = () =>
  http.post<WorkspaceScanResponse>('/metadata/workspaces/scan', null, { timeout: 300_000 })

// ── Search (ChromaDB) ───────────────────────────────────

export const semanticSearch = (query: string, topK = 10, scope = 'all') =>
  http.post<SearchResponse>('/search', { query, top_k: topK, scope })

export const getIndexStats = () =>
  http.get<IndexStats>('/search/stats')

export const reindexAll = () =>
  http.post<{ success: boolean; software_indexed: number; workspace_indexed: number; message: string }>('/search/reindex')

// ── OS Bridge (Module A) ────────────────────────────────

export const launchApp = (targetPath: string) =>
  http.post('/os/launch', { target_path: targetPath })

export const openDir = (targetPath: string) =>
  http.post('/os/open-dir', { target_path: targetPath })

export const browseDir = (path?: string) =>
  http.post<BrowseDirResponse>('/os/browse-dir', { path: path || null })

// ── Logs ─────────────────────────────────────────────────

export interface LogEntry {
  id: number
  timestamp: string
  level: string
  logger: string
  message: string
}

export const getLogs = (limit = 200) =>
  http.get<{ logs: LogEntry[] }>('/logs', { params: { limit } })
