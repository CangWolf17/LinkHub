<template>
  <div class="max-w-2xl">
    <!-- 白名单目录管理 -->
    <h2 class="text-xl font-bold text-gray-900 mb-6">白名单目录</h2>
    <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-8">
      <p class="text-sm text-gray-500 mb-4">
        LinkHub 只在这些目录中扫描和管理软件与工作区。每个目录需指定类型：软件仓（扫描为软件）或工作区（扫描为工作区）。
      </p>

      <div class="space-y-2 mb-3">
        <div
          v-for="(_d, i) in allowedDirs"
          :key="i"
          class="flex items-center gap-2"
        >
          <select
            v-model="allowedDirs[i].type"
            class="w-24 shrink-0 px-2 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
          >
            <option value="software">软件仓</option>
            <option value="workspace">工作区</option>
          </select>
          <input
            v-model="allowedDirs[i].path"
            type="text"
            :placeholder="allowedDirs[i].type === 'software' ? '例: C:\\MyPortableApps' : '例: C:\\Projects'"
            class="flex-1 px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button
            type="button"
            class="p-2 text-gray-400 hover:text-blue-500 transition-colors"
            @click="openFolderPicker(i)"
            title="浏览..."
          >
            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
            </svg>
          </button>
          <button
            type="button"
            class="p-2 text-gray-400 hover:text-red-500 transition-colors"
            @click="removeAllowedDir(i)"
            title="移除"
          >
            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>

      <button
        type="button"
        class="flex items-center gap-1.5 text-sm text-blue-600 hover:text-blue-700 font-medium mb-4"
        @click="addAllowedDir"
      >
        <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
        </svg>
        添加目录
      </button>

      <div class="flex items-center gap-3">
        <button
          class="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
          :disabled="savingDirs"
          @click="saveAllowedDirs"
        >
          {{ savingDirs ? '保存中...' : '保存目录' }}
        </button>
      </div>

      <p v-if="dirsError" class="mt-3 text-xs text-red-600">{{ dirsError }}</p>
      <p v-if="dirsSuccess" class="mt-3 text-xs text-green-600">{{ dirsSuccess }}</p>
    </div>

    <h2 class="text-xl font-bold text-gray-900 mb-6">LLM 模型配置</h2>

    <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6 space-y-5">
      <!-- Base URL -->
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-1">API Base URL</label>
        <input
          v-model="form.llm_base_url"
          type="text"
          placeholder="例: http://localhost:11434/v1"
          class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
      </div>

      <!-- API Key -->
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-1">API Key</label>
        <div class="relative">
          <input
            v-model="form.llm_api_key"
            :type="showKey ? 'text' : 'password'"
            placeholder="sk-..."
            class="w-full px-3 py-2 pr-10 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
          <button
            type="button"
            class="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 p-1"
            @click="showKey = !showKey"
          >
            <svg v-if="!showKey" class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
            </svg>
            <svg v-else class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.878 9.878L6.59 6.59m7.532 7.532l3.29 3.29M3 3l18 18" />
            </svg>
          </button>
        </div>
        <p v-if="currentConfig?.has_api_key" class="mt-1 text-xs text-green-600">
          已配置 API Key (如需更新请输入新值)
        </p>
      </div>

      <!-- Chat Model -->
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-1">Chat 模型</label>
        <input
          v-model="form.model_chat"
          type="text"
          placeholder="例: gpt-4o / qwen2.5:7b"
          class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
      </div>

      <!-- Embedding Model -->
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-1">Embedding 模型</label>
        <input
          v-model="form.model_embedding"
          type="text"
          placeholder="例: text-embedding-ada-002 / nomic-embed-text"
          class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
      </div>

      <!-- Max Tokens -->
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-1">
          Max Tokens
          <span class="text-xs text-gray-400 font-normal ml-1">AI 生成描述时的最大 token 数（推理模型建议 2048+）</span>
        </label>
        <input
          v-model.number="form.llm_max_tokens"
          type="number"
          min="64"
          max="32768"
          step="64"
          placeholder="1024"
          class="w-48 px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
      </div>

      <!-- System Prompt: 软件描述 -->
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-1">
          软件描述 System Prompt
          <span class="text-xs text-gray-400 font-normal ml-1">AI 生成软件描述时使用的系统提示词</span>
        </label>
        <textarea
          v-model="form.llm_system_prompt_software"
          rows="3"
          placeholder="留空则使用内置默认 prompt"
          class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-y"
        />
      </div>

      <!-- System Prompt: 工作区描述 -->
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-1">
          工作区描述 System Prompt
          <span class="text-xs text-gray-400 font-normal ml-1">AI 生成工作区描述时使用的系统提示词</span>
        </label>
        <textarea
          v-model="form.llm_system_prompt_workspace"
          rows="3"
          placeholder="留空则使用内置默认 prompt"
          class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-y"
        />
      </div>

      <!-- 按钮 -->
      <div class="flex items-center gap-3 pt-2">
        <button
          class="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          :disabled="saving"
          @click="saveConfig"
        >
          {{ saving ? '保存中...' : '保存配置' }}
        </button>

        <button
          class="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          :disabled="testing"
          @click="testConnection"
        >
          {{ testing ? '测试中...' : '测试连接' }}
        </button>
      </div>

      <!-- 状态消息 -->
      <div v-if="message" class="p-3 rounded-lg text-sm" :class="messageClass">
        {{ message }}
      </div>
    </div>

    <!-- 向量索引管理 -->
    <h3 class="text-lg font-bold text-gray-900 mt-8 mb-2">向量索引管理</h3>
    <p class="text-sm text-gray-500 mb-4">
      向量索引用于语义搜索功能。当软件或工作区记录变更后，索引可能与数据库不同步。点击「重建全部索引」会清空现有索引并根据当前数据库记录重新生成，不会影响软件和工作区的原始数据。
    </p>
    <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <div class="flex items-center gap-6 mb-4">
        <div class="text-sm">
          <span class="text-gray-500">软件索引:</span>
          <span class="ml-1 font-medium text-gray-900">{{ stats.software_count }}</span> 条
        </div>
        <div class="text-sm">
          <span class="text-gray-500">工作区索引:</span>
          <span class="ml-1 font-medium text-gray-900">{{ stats.workspace_count }}</span> 条
        </div>
      </div>
      <button
        class="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 disabled:opacity-50 transition-colors"
        :disabled="reindexing"
        @click="doReindex"
      >
        {{ reindexing ? '重建中...' : '重建全部索引' }}
      </button>
      <p v-if="reindexMsg" class="mt-2 text-xs text-green-600">{{ reindexMsg }}</p>
    </div>

    <!-- 初始化扫描 -->
    <h3 class="text-lg font-bold text-gray-900 mt-8 mb-2">初始化导入</h3>
    <p class="text-sm text-gray-500 mb-4">
      扫描白名单目录（allowed_dirs），将已有的便携软件和工作区目录批量导入数据库。已存在的记录会自动跳过。
    </p>
    <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6 space-y-5">
      <!-- 软件扫描 -->
      <div>
        <div class="flex items-center gap-3">
          <button
            class="px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 disabled:opacity-50 transition-colors"
            :disabled="scanningApps"
            @click="doScanApps"
          >
            {{ scanningApps ? '扫描中...' : '扫描导入软件' }}
          </button>
          <span v-if="scanAppsResult" class="text-sm" :class="scanAppsResult.success ? 'text-green-600' : 'text-red-600'">
            {{ scanAppsResult.message }}
          </span>
        </div>
        <div v-if="scanAppsResult && scanAppsResult.details.length" class="mt-3 max-h-48 overflow-y-auto border border-gray-100 rounded-lg divide-y divide-gray-50">
          <div
            v-for="d in scanAppsResult.details"
            :key="d.name"
            class="flex items-center gap-2 px-3 py-1.5 text-xs"
          >
            <span
              class="w-14 shrink-0 text-center rounded-full px-1.5 py-0.5 font-medium"
              :class="{
                'bg-green-100 text-green-700': d.status === 'imported',
                'bg-gray-100 text-gray-500': d.status === 'skipped',
                'bg-red-100 text-red-600': d.status === 'failed',
              }"
            >{{ d.status === 'imported' ? '导入' : d.status === 'skipped' ? '跳过' : '失败' }}</span>
            <span class="text-gray-800 truncate">{{ d.name }}</span>
            <span v-if="d.reason" class="text-gray-400 ml-auto shrink-0">{{ d.reason }}</span>
          </div>
        </div>
      </div>

      <!-- 工作区扫描 -->
      <div class="border-t border-gray-100 pt-5">
        <div class="flex items-center gap-3">
          <button
            class="px-4 py-2 text-sm font-medium text-white bg-teal-600 rounded-lg hover:bg-teal-700 disabled:opacity-50 transition-colors"
            :disabled="scanningWs"
            @click="doScanWorkspaces"
          >
            {{ scanningWs ? '扫描中...' : '扫描导入工作区' }}
          </button>
          <span v-if="scanWsResult" class="text-sm" :class="scanWsResult.success ? 'text-green-600' : 'text-red-600'">
            {{ scanWsResult.message }}
          </span>
        </div>
        <div v-if="scanWsResult && scanWsResult.details.length" class="mt-3 max-h-48 overflow-y-auto border border-gray-100 rounded-lg divide-y divide-gray-50">
          <div
            v-for="d in scanWsResult.details"
            :key="d.name"
            class="flex items-center gap-2 px-3 py-1.5 text-xs"
          >
            <span
              class="w-14 shrink-0 text-center rounded-full px-1.5 py-0.5 font-medium"
              :class="{
                'bg-green-100 text-green-700': d.status === 'imported',
                'bg-gray-100 text-gray-500': d.status === 'skipped',
              }"
            >{{ d.status === 'imported' ? '导入' : '跳过' }}</span>
            <span class="text-gray-800 truncate">{{ d.name }}</span>
            <span v-if="d.reason" class="text-gray-400 ml-auto shrink-0">{{ d.reason }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 服务管理 -->
    <h3 class="text-lg font-bold text-gray-900 mt-8 mb-2">服务管理</h3>
    <p class="text-sm text-gray-500 mb-4">
      关闭 LinkHub 后端服务。所有数据已自动保存，关闭后浏览器页面将无法访问后端接口。
    </p>
    <div class="bg-white rounded-xl shadow-sm border border-red-200 p-6">
      <div class="flex items-center justify-between">
        <div>
          <p class="text-sm font-medium text-gray-900">关闭所有服务</p>
          <p class="text-xs text-gray-500 mt-1">终止 LinkHub 后端进程，释放端口和系统资源</p>
        </div>
        <button
          class="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 disabled:opacity-50 transition-colors"
          :disabled="shuttingDown"
          @click="confirmShutdown"
        >
          {{ shuttingDown ? '正在关闭...' : '关闭服务' }}
        </button>
      </div>
      <p v-if="shutdownMsg" class="mt-3 text-xs text-red-600">{{ shutdownMsg }}</p>
    </div>

    <!-- 文件夹选择器弹窗 -->
    <FolderPickerDialog
      v-if="folderPickerIndex !== null"
      :initial-path="allowedDirs[folderPickerIndex]?.path"
      @confirm="onFolderPicked"
      @cancel="folderPickerIndex = null"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { getLlmConfig, updateLlmConfig, testLlmConnection, getIndexStats, reindexAll, scanAndImportSoftware, scanAndImportWorkspaces, getAllowedDirs, updateAllowedDirs, shutdownServer } from '@/api'
import type { LlmConfig, IndexStats, ScanDirsResponse, WorkspaceScanResponse, DirEntry } from '@/api'
import FolderPickerDialog from '@/components/FolderPickerDialog.vue'

// ── 白名单目录管理 ─────────────────────────────────────
const allowedDirs = ref<DirEntry[]>([{ path: '', type: 'software' }])
const savingDirs = ref(false)
const dirsError = ref('')
const dirsSuccess = ref('')

async function loadAllowedDirs() {
  try {
    const { data } = await getAllowedDirs()
    allowedDirs.value = data.allowed_dirs.length ? data.allowed_dirs : [{ path: '', type: 'software' }]
  } catch { /* ignore */ }
}

function addAllowedDir() {
  allowedDirs.value.push({ path: '', type: 'software' })
}

function removeAllowedDir(i: number) {
  allowedDirs.value.splice(i, 1)
  if (allowedDirs.value.length === 0) allowedDirs.value.push({ path: '', type: 'software' })
}

// 文件夹选择器
const folderPickerIndex = ref<number | null>(null)

function openFolderPicker(i: number) {
  folderPickerIndex.value = i
}

function onFolderPicked(path: string) {
  if (folderPickerIndex.value !== null && folderPickerIndex.value < allowedDirs.value.length) {
    allowedDirs.value[folderPickerIndex.value].path = path
  }
  folderPickerIndex.value = null
}

async function saveAllowedDirs() {
  const cleaned = allowedDirs.value
    .map(d => ({ path: d.path.trim(), type: d.type }))
    .filter(d => d.path)
  if (cleaned.length === 0) {
    dirsError.value = '请至少填写一个工作目录'
    return
  }
  dirsError.value = ''
  dirsSuccess.value = ''
  savingDirs.value = true
  try {
    await updateAllowedDirs(cleaned)
    allowedDirs.value = cleaned
    dirsSuccess.value = '目录列表已保存'
    setTimeout(() => { dirsSuccess.value = '' }, 3000)
  } catch {
    dirsError.value = '保存失败，请重试'
  } finally {
    savingDirs.value = false
  }
}

// ── LLM 配置 ──────────────────────────────────────────

const currentConfig = ref<LlmConfig | null>(null)
const form = reactive({
  llm_base_url: '',
  llm_api_key: '',
  model_chat: '',
  model_embedding: '',
  llm_max_tokens: 1024,
  llm_system_prompt_software: '',
  llm_system_prompt_workspace: '',
})
const showKey = ref(false)
const saving = ref(false)
const testing = ref(false)
const message = ref('')
const messageType = ref<'success' | 'error'>('success')

const messageClass = computed(() =>
  messageType.value === 'success'
    ? 'bg-green-50 text-green-700 border border-green-200'
    : 'bg-red-50 text-red-700 border border-red-200',
)

const stats = reactive<IndexStats>({ software_count: 0, workspace_count: 0 })
const reindexing = ref(false)
const reindexMsg = ref('')

const scanningApps = ref(false)
const scanAppsResult = ref<ScanDirsResponse | null>(null)
const scanningWs = ref(false)
const scanWsResult = ref<WorkspaceScanResponse | null>(null)

async function loadConfig() {
  try {
    const { data } = await getLlmConfig()
    currentConfig.value = data
    form.llm_base_url = data.llm_base_url
    form.llm_api_key = '' // 不回显 key
    form.model_chat = data.model_chat
    form.model_embedding = data.model_embedding
    form.llm_max_tokens = data.llm_max_tokens ?? 1024
    form.llm_system_prompt_software = data.llm_system_prompt_software || ''
    form.llm_system_prompt_workspace = data.llm_system_prompt_workspace || ''
  } catch {
    showMsg('加载配置失败', 'error')
  }
}

async function loadStats() {
  try {
    const { data } = await getIndexStats()
    stats.software_count = data.software_count
    stats.workspace_count = data.workspace_count
  } catch { /* ignore */ }
}

async function saveConfig() {
  saving.value = true
  message.value = ''
  try {
    const payload: Record<string, string | number> = {}
    if (form.llm_base_url) payload.llm_base_url = form.llm_base_url
    if (form.llm_api_key) payload.llm_api_key = form.llm_api_key
    if (form.model_chat) payload.model_chat = form.model_chat
    if (form.model_embedding) payload.model_embedding = form.model_embedding
    payload.llm_max_tokens = form.llm_max_tokens
    // system prompt 允许清空（传空字符串恢复默认）
    if (form.llm_system_prompt_software !== undefined) payload.llm_system_prompt_software = form.llm_system_prompt_software
    if (form.llm_system_prompt_workspace !== undefined) payload.llm_system_prompt_workspace = form.llm_system_prompt_workspace

    await updateLlmConfig(payload)
    showMsg('配置已保存', 'success')
    await loadConfig()
  } catch (e: unknown) {
    const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '保存失败'
    showMsg(msg, 'error')
  } finally {
    saving.value = false
  }
}

async function testConnection() {
  testing.value = true
  message.value = ''
  try {
    const { data } = await testLlmConnection()
    showMsg(`连接成功: ${data.message || data.model}`, 'success')
  } catch (e: unknown) {
    const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '连接失败'
    showMsg(detail, 'error')
  } finally {
    testing.value = false
  }
}

async function doReindex() {
  reindexing.value = true
  reindexMsg.value = ''
  try {
    const { data } = await reindexAll()
    reindexMsg.value = data.message
    await loadStats()
  } catch {
    reindexMsg.value = '重建索引失败'
  } finally {
    reindexing.value = false
  }
}

async function doScanApps() {
  scanningApps.value = true
  scanAppsResult.value = null
  try {
    const { data } = await scanAndImportSoftware()
    scanAppsResult.value = data
    await loadStats()
  } catch {
    scanAppsResult.value = { success: false, imported: 0, skipped: 0, failed: 0, details: [], message: '扫描失败，请检查服务日志' }
  } finally {
    scanningApps.value = false
  }
}

async function doScanWorkspaces() {
  scanningWs.value = true
  scanWsResult.value = null
  try {
    const { data } = await scanAndImportWorkspaces()
    scanWsResult.value = data
    await loadStats()
  } catch {
    scanWsResult.value = { success: false, imported: 0, skipped: 0, details: [], message: '扫描失败，请检查服务日志' }
  } finally {
    scanningWs.value = false
  }
}

function showMsg(msg: string, type: 'success' | 'error') {
  message.value = msg
  messageType.value = type
  setTimeout(() => { message.value = '' }, 5000)
}

// ── 服务管理 ─────────────────────────────────────────────
const shuttingDown = ref(false)
const shutdownMsg = ref('')

async function confirmShutdown() {
  if (!confirm('确定要关闭 LinkHub 服务吗？关闭后需要重新启动程序才能使用。')) return
  shuttingDown.value = true
  shutdownMsg.value = ''
  try {
    await shutdownServer()
    shutdownMsg.value = '服务正在关闭，页面即将失去连接...'
  } catch {
    // 服务关闭后请求可能超时，这是正常的
    shutdownMsg.value = '服务已关闭'
  }
}

onMounted(() => {
  loadAllowedDirs()
  loadConfig()
  loadStats()
})
</script>
