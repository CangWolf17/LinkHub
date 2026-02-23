<template>
  <!-- 遮罩 -->
  <Teleport to="body">
    <div
      v-if="visible"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
    >
      <div class="w-full max-w-lg mx-4 bg-white rounded-2xl shadow-2xl overflow-hidden">

        <!-- 顶部进度条 -->
        <div class="h-1 bg-gray-100">
          <div
            class="h-1 bg-blue-500 transition-all duration-500"
            :style="{ width: `${(step / totalSteps) * 100}%` }"
          />
        </div>

        <!-- 步骤指示 -->
        <div class="flex items-center justify-between px-6 pt-5 pb-1">
          <div class="flex items-center gap-2">
            <span
              v-for="n in totalSteps"
              :key="n"
              class="flex items-center justify-center w-7 h-7 rounded-full text-xs font-bold transition-colors"
              :class="n < step
                ? 'bg-blue-500 text-white'
                : n === step
                  ? 'bg-blue-600 text-white ring-2 ring-blue-200'
                  : 'bg-gray-100 text-gray-400'"
            >
              <Check v-if="n < step" :size="14" />
              <span v-else>{{ n }}</span>
            </span>
          </div>
          <span class="text-xs text-gray-400">{{ step }} / {{ totalSteps }}</span>
        </div>

        <!-- ── Step 1: 工作目录 ── -->
        <div v-if="step === 1" class="px-6 pt-4 pb-6">
          <h2 class="text-lg font-bold text-gray-900 mb-1">欢迎使用 LinkHub</h2>
          <p class="text-sm text-gray-500 mb-4">
            首先设置你的工作目录白名单。LinkHub 将只在这些目录中扫描和管理软件与工作区。
          </p>

          <!-- 导入配置快捷入口 -->
          <div class="mb-5 p-3 bg-blue-50 rounded-xl border border-blue-100">
            <div class="flex items-center justify-between">
              <div>
                <div class="text-sm font-medium text-blue-800">已有配置文件？</div>
                <div class="text-xs text-blue-600 mt-0.5">导入后自动跳过向导</div>
              </div>
              <label class="px-3 py-1.5 text-sm font-medium text-blue-700 bg-white rounded-lg border border-blue-200 hover:bg-blue-50 cursor-pointer transition-colors">
                导入配置
                <input type="file" accept=".json" class="hidden" @change="handleImportConfig" />
              </label>
            </div>
            <p v-if="importError" class="mt-2 text-xs text-red-600">{{ importError }}</p>
          </div>

          <label class="block text-sm font-medium text-gray-700 mb-2">工作目录列表</label>

          <!-- 目录列表 -->
          <div class="space-y-2 mb-3">
            <div
              v-for="(_dir, i) in dirs"
              :key="i"
              class="flex items-center gap-2"
            >
              <select
                v-model="dirs[i].type"
                class="w-24 shrink-0 px-2 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
              >
                <option value="software">软件仓</option>
                <option value="workspace">工作区</option>
              </select>
              <input
                v-model="dirs[i].path"
                type="text"
                :placeholder="dirs[i].type === 'software' ? '例: C:\\MyPortableApps' : '例: C:\\Projects'"
                class="flex-1 px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <button
                type="button"
                class="p-2 text-gray-400 hover:text-blue-500 transition-colors"
                @click="openFolderPicker(i)"
                title="浏览..."
              >
                <FolderOpen :size="16" />
              </button>
              <button
                type="button"
                class="p-2 text-gray-400 hover:text-red-500 transition-colors"
                @click="removeDir(i)"
                title="移除"
              >
                <X :size="16" />
              </button>
            </div>
          </div>

          <button
            type="button"
            class="flex items-center gap-1.5 text-sm text-blue-600 hover:text-blue-700 font-medium mb-5"
            @click="addDir"
          >
            <Plus :size="16" />
            添加目录
          </button>

          <p v-if="step1Error" class="mb-3 text-xs text-red-600">{{ step1Error }}</p>

          <div class="flex justify-end gap-2">
            <button
              class="px-4 py-2 text-sm text-gray-500 hover:text-gray-700"
              @click="skipAll"
            >
              跳过向导
            </button>
            <button
              class="px-5 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
              :disabled="saving"
              @click="submitStep1"
            >
              {{ saving ? '保存中...' : '下一步' }}
            </button>
          </div>
        </div>

        <!-- ── Step 2: LLM 配置 ── -->
        <div v-if="step === 2" class="px-6 pt-4 pb-6">
          <h2 class="text-lg font-bold text-gray-900 mb-1">配置 LLM 模型</h2>
          <p class="text-sm text-gray-500 mb-5">
            连接你的 AI 模型提供商。LLM 用于自动生成软件描述，语义搜索使用本地 embedding 模型，无需此配置。
          </p>

          <div class="space-y-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">API Base URL</label>
              <ApiUrlCombobox
                v-model="llm.base_url"
                :options="LLM_API_PRESETS"
                placeholder="选择或输入 API 地址"
              />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">API Key</label>
              <div class="relative">
                <input
                  v-model="llm.api_key"
                  :type="showKey ? 'text' : 'password'"
                  placeholder="sk-..."
                  class="w-full px-3 py-2 pr-10 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <button
                  type="button"
                  class="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-gray-400 hover:text-gray-600"
                  @click="showKey = !showKey"
                >
                  <Eye v-if="!showKey" :size="16" />
                  <EyeOff v-else :size="16" />
                </button>
              </div>
            </div>
            <div class="grid grid-cols-2 gap-3">
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">Chat 模型</label>
                <input
                  v-model="llm.model_chat"
                  type="text"
                  placeholder="gpt-4o"
                  class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">Embedding 模型</label>
                <input
                  v-model="llm.model_embedding"
                  type="text"
                  placeholder="text-embedding-ada-002"
                  class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
          </div>

          <p v-if="step2Error" class="mt-3 text-xs text-red-600">{{ step2Error }}</p>
          <p v-if="step2Success" class="mt-3 text-xs text-green-600">{{ step2Success }}</p>

          <div class="flex justify-between mt-5">
            <button
              class="px-4 py-2 text-sm text-gray-500 hover:text-gray-700"
              @click="step = 1"
            >
              上一步
            </button>
            <div class="flex gap-2">
              <button
                class="px-4 py-2 text-sm text-gray-500 hover:text-gray-700"
                @click="step = 3"
              >
                跳过
              </button>
              <button
                class="px-5 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
                :disabled="savingLlm"
                @click="submitStep2"
              >
                {{ savingLlm ? '保存中...' : '下一步' }}
              </button>
            </div>
          </div>
        </div>

        <!-- ── Step 3: 扫描导入 ── -->
        <div v-if="step === 3" class="px-6 pt-4 pb-6">
          <h2 class="text-lg font-bold text-gray-900 mb-1">导入已有内容</h2>
          <p class="text-sm text-gray-500 mb-5">
            自动扫描白名单目录，将已有的软件和工作区目录批量导入。此步骤可跳过，之后在设置页随时触发。
          </p>

          <div class="space-y-3 mb-5">
            <!-- 扫描软件 -->
            <div class="flex items-center justify-between p-3 bg-gray-50 rounded-xl">
              <div>
                <div class="text-sm font-medium text-gray-800">扫描导入软件</div>
                <div class="text-xs text-gray-400 mt-0.5">
                  <span v-if="!scanAppsDone">将识别各子目录中的可执行文件</span>
                  <span v-else class="text-green-600">{{ scanAppsMsg }}</span>
                </div>
              </div>
              <button
                class="px-3 py-1.5 text-sm font-medium text-white bg-indigo-500 rounded-lg hover:bg-indigo-600 disabled:opacity-50 transition-colors"
                :disabled="scanningApps || scanAppsDone"
                @click="doScanApps"
              >
                {{ scanningApps ? '扫描中...' : scanAppsDone ? '完成' : '扫描' }}
              </button>
            </div>

            <!-- 扫描工作区 -->
            <div class="flex items-center justify-between p-3 bg-gray-50 rounded-xl">
              <div>
                <div class="text-sm font-medium text-gray-800">扫描导入工作区</div>
                <div class="text-xs text-gray-400 mt-0.5">
                  <span v-if="!scanWsDone">将各子目录注册为工作区记录</span>
                  <span v-else class="text-green-600">{{ scanWsMsg }}</span>
                </div>
              </div>
              <button
                class="px-3 py-1.5 text-sm font-medium text-white bg-teal-500 rounded-lg hover:bg-teal-600 disabled:opacity-50 transition-colors"
                :disabled="scanningWs || scanWsDone"
                @click="doScanWs"
              >
                {{ scanningWs ? '扫描中...' : scanWsDone ? '完成' : '扫描' }}
              </button>
            </div>
          </div>

          <div class="flex justify-between">
            <button
              class="px-4 py-2 text-sm text-gray-500 hover:text-gray-700"
              @click="step = 2"
            >
              上一步
            </button>
            <button
              class="px-5 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors"
              @click="finish"
            >
              完成设置
            </button>
          </div>
        </div>

      </div>
    </div>
  </Teleport>

  <!-- 文件夹选择器弹窗 -->
  <FolderPickerDialog
    v-if="folderPickerIndex !== null"
    :initial-path="dirs[folderPickerIndex]?.path"
    @confirm="onFolderPicked"
    @cancel="folderPickerIndex = null"
  />
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import {
  updateAllowedDirs,
  updateLlmConfig,
  scanAndImportSoftware,
  scanAndImportWorkspaces,
  importSettings,
} from '@/api'
import type { DirEntry } from '@/api'
import FolderPickerDialog from '@/components/FolderPickerDialog.vue'
import ApiUrlCombobox from '@/components/ApiUrlCombobox.vue'
import { LLM_API_PRESETS } from '@/constants/llmPresets'
import { Check, FolderOpen, X, Plus, Eye, EyeOff } from 'lucide-vue-next'

const emit = defineEmits<{ (e: 'done'): void }>()

const visible = ref(true)
const totalSteps = 3
const step = ref(1)

// ── Step 1 state ─────────────────────────────
const dirs = ref<DirEntry[]>([{ path: '', type: 'software' }])
const saving = ref(false)
const step1Error = ref('')

// 导入配置
const importError = ref('')

async function handleImportConfig(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return

  importError.value = ''
  try {
    const text = await file.text()
    const config = JSON.parse(text)
    if (!config._export_source || config._export_source !== 'LinkHub') {
      importError.value = '不是有效的 LinkHub 配置文件'
      return
    }
    await importSettings(config)
    visible.value = false
    emit('done')
  } catch {
    importError.value = '导入失败：文件格式错误'
  } finally {
    input.value = ''
  }
}

function addDir() {
  dirs.value.push({ path: '', type: 'software' })
}

function removeDir(i: number) {
  dirs.value.splice(i, 1)
  if (dirs.value.length === 0) dirs.value.push({ path: '', type: 'software' })
}

// 文件夹选择器
const folderPickerIndex = ref<number | null>(null)

function openFolderPicker(i: number) {
  folderPickerIndex.value = i
}

function onFolderPicked(path: string) {
  if (folderPickerIndex.value !== null && folderPickerIndex.value < dirs.value.length) {
    dirs.value[folderPickerIndex.value].path = path
  }
  folderPickerIndex.value = null
}

async function submitStep1() {
  const cleaned = dirs.value
    .map(d => ({ path: d.path.trim(), type: d.type }))
    .filter(d => d.path)
  if (cleaned.length === 0) {
    step1Error.value = '请至少填写一个工作目录'
    return
  }
  step1Error.value = ''
  saving.value = true
  try {
    await updateAllowedDirs(cleaned)
    step.value = 2
  } catch {
    step1Error.value = '保存失败，请重试'
  } finally {
    saving.value = false
  }
}

// ── Step 2 state ─────────────────────────────
const llm = reactive({
  base_url: '',
  api_key: '',
  model_chat: '',
  model_embedding: '',
})
const showKey = ref(false)
const savingLlm = ref(false)
const step2Error = ref('')
const step2Success = ref('')

async function submitStep2() {
  if (!llm.base_url.trim()) {
    step2Error.value = '请填写 API Base URL'
    return
  }
  step2Error.value = ''
  savingLlm.value = true
  try {
    const payload: Record<string, string> = { llm_base_url: llm.base_url }
    if (llm.api_key) payload.llm_api_key = llm.api_key
    if (llm.model_chat) payload.model_chat = llm.model_chat
    if (llm.model_embedding) payload.model_embedding = llm.model_embedding
    await updateLlmConfig(payload)
    step2Success.value = '配置已保存'
    setTimeout(() => { step.value = 3 }, 600)
  } catch {
    step2Error.value = '保存失败，请重试'
  } finally {
    savingLlm.value = false
  }
}

// ── Step 3 state ─────────────────────────────
const scanningApps = ref(false)
const scanAppsDone = ref(false)
const scanAppsMsg = ref('')
const scanningWs = ref(false)
const scanWsDone = ref(false)
const scanWsMsg = ref('')

async function doScanApps() {
  scanningApps.value = true
  try {
    const { data } = await scanAndImportSoftware()
    scanAppsMsg.value = data.message
    scanAppsDone.value = true
  } catch {
    scanAppsMsg.value = '扫描失败'
    scanAppsDone.value = true
  } finally {
    scanningApps.value = false
  }
}

async function doScanWs() {
  scanningWs.value = true
  try {
    const { data } = await scanAndImportWorkspaces()
    scanWsMsg.value = data.message
    scanWsDone.value = true
  } catch {
    scanWsMsg.value = '扫描失败'
    scanWsDone.value = true
  } finally {
    scanningWs.value = false
  }
}

function finish() {
  visible.value = false
  emit('done')
}

function skipAll() {
  visible.value = false
  emit('done')
}
</script>
