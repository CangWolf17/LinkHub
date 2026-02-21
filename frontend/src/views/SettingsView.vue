<template>
  <div class="max-w-2xl">
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
    <h3 class="text-lg font-bold text-gray-900 mt-8 mb-4">向量索引管理</h3>
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
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { getLlmConfig, updateLlmConfig, testLlmConnection, getIndexStats, reindexAll, scanAndImportSoftware, scanAndImportWorkspaces } from '@/api'
import type { LlmConfig, IndexStats, ScanDirsResponse, WorkspaceScanResponse } from '@/api'

const currentConfig = ref<LlmConfig | null>(null)
const form = reactive({
  llm_base_url: '',
  llm_api_key: '',
  model_chat: '',
  model_embedding: '',
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
    const payload: Record<string, string> = {}
    if (form.llm_base_url) payload.llm_base_url = form.llm_base_url
    if (form.llm_api_key) payload.llm_api_key = form.llm_api_key
    if (form.model_chat) payload.model_chat = form.model_chat
    if (form.model_embedding) payload.model_embedding = form.model_embedding

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

onMounted(() => {
  loadConfig()
  loadStats()
})
</script>
