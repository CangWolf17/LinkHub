<template>
  <div class="max-w-3xl">
    <!-- 标签栏 -->
    <div class="flex items-center gap-1 border-b border-gray-200 mb-6">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        class="px-4 py-2.5 text-sm font-medium transition-colors relative"
        :class="activeTab === tab.key
          ? 'text-blue-600'
          : 'text-gray-500 hover:text-gray-700'"
        @click="activeTab = tab.key"
      >
        {{ tab.label }}
        <div
          v-if="activeTab === tab.key"
          class="absolute bottom-0 left-0 right-0 h-0.5 bg-blue-600 rounded-full"
        />
      </button>
    </div>

    <!-- ═══ Tab: 目录 ═══ -->
    <div v-if="activeTab === 'dirs'">
      <h2 class="text-lg font-bold text-gray-900 mb-2">白名单目录</h2>
      <p class="text-sm text-gray-500 mb-4">
        LinkHub 只在这些目录中扫描和管理软件与工作区。每个目录需指定类型：软件仓或工作区。
      </p>
      <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
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
              <FolderOpen :size="16" />
            </button>
            <button
              type="button"
              class="p-2 text-gray-400 hover:text-red-500 transition-colors"
              @click="removeAllowedDir(i)"
              title="移除"
            >
              <X :size="16" />
            </button>
          </div>
        </div>

        <button
          type="button"
          class="flex items-center gap-1.5 text-sm text-blue-600 hover:text-blue-700 font-medium mb-4"
          @click="addAllowedDir"
        >
          <Plus :size="16" />
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

      <!-- 批量导入 -->
      <h2 class="text-lg font-bold text-gray-900 mt-8 mb-2">批量导入</h2>
      <p class="text-sm text-gray-500 mb-4">
        扫描白名单目录，将已有的便携软件和工作区目录批量导入数据库。已存在的记录会自动跳过。
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

    <!-- ═══ Tab: LLM ═══ -->
    <div v-if="activeTab === 'llm'">
      <h2 class="text-lg font-bold text-gray-900 mb-2">LLM 模型配置</h2>
      <p class="text-sm text-gray-500 mb-4">
        连接 AI 模型提供商，用于自动生成软件和工作区描述。
      </p>
      <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6 space-y-5">
        <!-- Base URL -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">API Base URL</label>
          <ApiUrlCombobox
            v-model="form.llm_base_url"
            :options="LLM_API_PRESETS"
            placeholder="选择或输入 API 地址"
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
              <Eye v-if="!showKey" :size="16" />
              <EyeOff v-else :size="16" />
            </button>
          </div>
          <p v-if="currentConfig?.has_api_key" class="mt-1 text-xs text-green-600">
            已配置 API Key (如需更新请输入新值)
          </p>
        </div>

        <!-- Chat Model / Embedding Model -->
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Chat 模型</label>
            <input
              v-model="form.model_chat"
              type="text"
              placeholder="例: gpt-4o / qwen2.5:7b"
              class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Embedding 模型</label>
            <input
              v-model="form.model_embedding"
              type="text"
              placeholder="例: text-embedding-ada-002"
              class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
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

        <!-- AI 批量黑名单: 软件 -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">
            软件 AI 黑名单
            <span class="text-xs text-gray-400 font-normal ml-1">名称匹配的软件将跳过 AI 批量操作</span>
          </label>

          <!-- 已选标签 -->
          <div v-if="form.ai_blacklist_software.length > 0" class="flex flex-wrap gap-1.5 mb-2">
            <span
              v-for="name in form.ai_blacklist_software"
              :key="name"
              class="inline-flex items-center gap-1 px-2 py-0.5 text-xs bg-red-50 text-red-700 rounded-full"
            >
              {{ name }}
              <button
                class="text-red-400 hover:text-red-600 transition-colors"
                @click="removeSoftwareBlacklist(name)"
              >
                <X :size="12" />
              </button>
            </span>
          </div>

          <!-- 卡片选择器 -->
          <div class="relative">
            <input
              v-model="swBlacklistSearch"
              type="text"
              placeholder="搜索并添加软件到黑名单..."
              class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              @focus="swBlacklistDropdownOpen = true"
              @input="swBlacklistDropdownOpen = true"
            />
            <!-- 下拉列表 -->
            <div
              v-if="swBlacklistDropdownOpen && filteredSwForBlacklist.length > 0"
              class="absolute z-10 w-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg max-h-40 overflow-y-auto"
            >
              <button
                v-for="sw in filteredSwForBlacklist"
                :key="sw.id"
                class="w-full flex items-center gap-2 px-3 py-1.5 text-left text-xs hover:bg-blue-50 transition-colors"
                @mousedown.prevent="addSoftwareBlacklist(sw.name)"
              >
                <span class="text-gray-400">+</span>
                <span class="text-gray-800 truncate">{{ sw.name }}</span>
              </button>
            </div>
          </div>
          <p class="text-xs text-gray-400 mt-1">当前 {{ form.ai_blacklist_software.length }} 项</p>
        </div>

        <!-- AI 批量黑名单: 工作区 -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">
            工作区 AI 黑名单
            <span class="text-xs text-gray-400 font-normal ml-1">名称匹配的工作区将跳过 AI 批量操作</span>
          </label>

          <!-- 已选标签 -->
          <div v-if="form.ai_blacklist_workspace.length > 0" class="flex flex-wrap gap-1.5 mb-2">
            <span
              v-for="name in form.ai_blacklist_workspace"
              :key="name"
              class="inline-flex items-center gap-1 px-2 py-0.5 text-xs bg-red-50 text-red-700 rounded-full"
            >
              {{ name }}
              <button
                class="text-red-400 hover:text-red-600 transition-colors"
                @click="removeWorkspaceBlacklist(name)"
              >
                <X :size="12" />
              </button>
            </span>
          </div>

          <!-- 卡片选择器 -->
          <div class="relative">
            <input
              v-model="wsBlacklistSearch"
              type="text"
              placeholder="搜索并添加工作区到黑名单..."
              class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              @focus="wsBlacklistDropdownOpen = true"
              @input="wsBlacklistDropdownOpen = true"
            />
            <!-- 下拉列表 -->
            <div
              v-if="wsBlacklistDropdownOpen && filteredWsForBlacklist.length > 0"
              class="absolute z-10 w-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg max-h-40 overflow-y-auto"
            >
              <button
                v-for="ws in filteredWsForBlacklist"
                :key="ws.id"
                class="w-full flex items-center gap-2 px-3 py-1.5 text-left text-xs hover:bg-blue-50 transition-colors"
                @mousedown.prevent="addWorkspaceBlacklist(ws.name)"
              >
                <span class="text-gray-400">+</span>
                <span class="text-gray-800 truncate">{{ ws.name }}</span>
              </button>
            </div>
          </div>
          <p class="text-xs text-gray-400 mt-1">当前 {{ form.ai_blacklist_workspace.length }} 项</p>
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
    </div>

    <!-- ═══ Tab: 索引 ═══ -->
    <div v-if="activeTab === 'index'">
      <h2 class="text-lg font-bold text-gray-900 mb-2">向量索引管理</h2>
      <p class="text-sm text-gray-500 mb-4">
        向量索引用于语义搜索功能。当软件或工作区记录变更后，索引可能与数据库不同步。点击「重建全部索引」会清空现有索引并根据当前数据库记录重新生成，不会影响原始数据。
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
    </div>

    <!-- ═══ Tab: 服务 ═══ -->
    <div v-if="activeTab === 'service'">
      <!-- 版本信息 -->
      <div class="flex items-center gap-3 mb-8 px-1">
        <span class="text-sm text-gray-500">LinkHub</span>
        <span class="text-sm font-medium text-gray-900">{{ appVersion || '...' }}</span>
      </div>

      <!-- 端口配置 -->
      <h2 class="text-lg font-bold text-gray-900 mb-2">端口配置</h2>
      <p class="text-sm text-gray-500 mb-4">
        修改 LinkHub 服务端口。修改后需要重启 LinkHub 才能生效。
      </p>
      <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-8">
        <div class="flex items-center gap-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">服务端口</label>
            <input
              v-model.number="portForm.port"
              type="number"
              min="1024"
              max="65535"
              class="w-36 px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div class="pt-5">
            <button
              class="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
              :disabled="savingPort"
              @click="savePort"
            >
              {{ savingPort ? '保存中...' : '保存' }}
            </button>
          </div>
        </div>
        <p v-if="portForm.port !== portForm.currentPort" class="mt-2 text-xs text-amber-600">
          当前运行端口: {{ portForm.currentPort }}。修改后需重启 LinkHub 生效。
        </p>
        <p v-if="portMsg" class="mt-2 text-xs" :class="portMsgType === 'success' ? 'text-green-600' : 'text-red-600'">{{ portMsg }}</p>
      </div>

      <!-- 配置导入导出 -->
      <h2 class="text-lg font-bold text-gray-900 mb-2">配置管理</h2>
      <p class="text-sm text-gray-500 mb-4">
        导出或导入 LinkHub 配置文件。导出包含系统设置、软件描述/标签和工作区元数据，不包含 API Key。
      </p>
      <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-8">
        <div class="flex items-center gap-3">
          <button
            class="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
            @click="exportConfig"
          >
            导出配置
          </button>
          <label
            class="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors cursor-pointer"
          >
            导入配置
            <input type="file" accept=".json" class="hidden" @change="importConfig" />
          </label>
        </div>
        <p v-if="configIoMsg" class="mt-2 text-xs" :class="configIoMsgType === 'success' ? 'text-green-600' : 'text-red-600'">{{ configIoMsg }}</p>
      </div>

      <!-- 关闭服务 -->
      <h2 class="text-lg font-bold text-gray-900 mb-2">服务管理</h2>
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
    </div>

    <!-- 文件夹选择器弹窗 -->
    <FolderPickerDialog
      v-if="folderPickerIndex !== null"
      :initial-path="allowedDirs[folderPickerIndex]?.path"
      @confirm="onFolderPicked"
      @cancel="folderPickerIndex = null"
    />
    <ConfirmDialog ref="confirmRef" />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onBeforeUnmount, computed } from 'vue'
import {
  getLlmConfig, updateLlmConfig, testLlmConnection,
  getIndexStats, reindexAll,
  scanAndImportSoftware, scanAndImportWorkspaces,
  getAllowedDirs, updateAllowedDirs,
  shutdownServer,
  getPortConfig, updatePortConfig,
  exportSettings, importSettings,
  getHealth,
  getSoftwareList, getWorkspaceList,
} from '@/api'
import type { LlmConfig, IndexStats, ScanDirsResponse, WorkspaceScanResponse, DirEntry, Software, Workspace } from '@/api'
import FolderPickerDialog from '@/components/FolderPickerDialog.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import ApiUrlCombobox from '@/components/ApiUrlCombobox.vue'
import { LLM_API_PRESETS } from '@/constants/llmPresets'
import { FolderOpen, X, Plus, Eye, EyeOff } from 'lucide-vue-next'

// ── 标签页 ───────────────────────────────────────────────
const tabs = [
  { key: 'dirs', label: '目录' },
  { key: 'llm', label: 'LLM' },
  { key: 'index', label: '索引' },
  { key: 'service', label: '服务' },
] as const

type TabKey = (typeof tabs)[number]['key']
const activeTab = ref<TabKey>('dirs')

// 确认弹窗
const confirmRef = ref<InstanceType<typeof ConfirmDialog> | null>(null)

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
  ai_blacklist_software: [] as string[],
  ai_blacklist_workspace: [] as string[],
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

// 黑名单: 卡片选择模式
const allSoftwareItems = ref<Software[]>([])
const allWorkspaceItems = ref<Workspace[]>([])
const swBlacklistSearch = ref('')
const wsBlacklistSearch = ref('')
const swBlacklistDropdownOpen = ref(false)
const wsBlacklistDropdownOpen = ref(false)

async function loadBlacklistCards() {
  try {
    const [swRes, wsRes] = await Promise.all([getSoftwareList(), getWorkspaceList()])
    allSoftwareItems.value = swRes.data.items
    allWorkspaceItems.value = wsRes.data.items
  } catch { /* ignore */ }
}

// 过滤出不在黑名单中的软件，支持搜索
const filteredSwForBlacklist = computed(() => {
  const blackSet = new Set(form.ai_blacklist_software.map(n => n.toLowerCase()))
  let list = allSoftwareItems.value.filter(sw => !blackSet.has(sw.name.toLowerCase()))
  if (swBlacklistSearch.value.trim()) {
    const q = swBlacklistSearch.value.toLowerCase()
    list = list.filter(sw => sw.name.toLowerCase().includes(q))
  }
  return list.slice(0, 20)
})

const filteredWsForBlacklist = computed(() => {
  const blackSet = new Set(form.ai_blacklist_workspace.map(n => n.toLowerCase()))
  let list = allWorkspaceItems.value.filter(ws => !blackSet.has(ws.name.toLowerCase()))
  if (wsBlacklistSearch.value.trim()) {
    const q = wsBlacklistSearch.value.toLowerCase()
    list = list.filter(ws => ws.name.toLowerCase().includes(q))
  }
  return list.slice(0, 20)
})

function addSoftwareBlacklist(name: string) {
  if (!form.ai_blacklist_software.includes(name)) {
    form.ai_blacklist_software.push(name)
  }
  swBlacklistSearch.value = ''
  swBlacklistDropdownOpen.value = false
}

function removeSoftwareBlacklist(name: string) {
  form.ai_blacklist_software = form.ai_blacklist_software.filter(n => n !== name)
}

function addWorkspaceBlacklist(name: string) {
  if (!form.ai_blacklist_workspace.includes(name)) {
    form.ai_blacklist_workspace.push(name)
  }
  wsBlacklistSearch.value = ''
  wsBlacklistDropdownOpen.value = false
}

function removeWorkspaceBlacklist(name: string) {
  form.ai_blacklist_workspace = form.ai_blacklist_workspace.filter(n => n !== name)
}

// 全局点击关闭下拉
function closeBlacklistDropdowns(e: MouseEvent) {
  const target = e.target as HTMLElement
  if (!target.closest('.relative')) {
    swBlacklistDropdownOpen.value = false
    wsBlacklistDropdownOpen.value = false
  }
}

async function loadConfig() {
  try {
    const { data } = await getLlmConfig()
    currentConfig.value = data
    form.llm_base_url = data.llm_base_url
    form.llm_api_key = ''
    form.model_chat = data.model_chat
    form.model_embedding = data.model_embedding
    form.llm_max_tokens = data.llm_max_tokens ?? 1024
    form.llm_system_prompt_software = data.llm_system_prompt_software || ''
    form.llm_system_prompt_workspace = data.llm_system_prompt_workspace || ''
    form.ai_blacklist_software = data.ai_blacklist_software || []
    form.ai_blacklist_workspace = data.ai_blacklist_workspace || []
  } catch {
    showMsg('加载配置失败', 'error')
  }
}

async function saveConfig() {
  saving.value = true
  message.value = ''
  try {
    const payload: Record<string, string | number | string[]> = {}
    if (form.llm_base_url) payload.llm_base_url = form.llm_base_url
    if (form.llm_api_key) payload.llm_api_key = form.llm_api_key
    if (form.model_chat) payload.model_chat = form.model_chat
    if (form.model_embedding) payload.model_embedding = form.model_embedding
    payload.llm_max_tokens = form.llm_max_tokens
    if (form.llm_system_prompt_software !== undefined) payload.llm_system_prompt_software = form.llm_system_prompt_software
    if (form.llm_system_prompt_workspace !== undefined) payload.llm_system_prompt_workspace = form.llm_system_prompt_workspace
    payload.ai_blacklist_software = form.ai_blacklist_software
    payload.ai_blacklist_workspace = form.ai_blacklist_workspace
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

function showMsg(msg: string, type: 'success' | 'error') {
  message.value = msg
  messageType.value = type
  setTimeout(() => { message.value = '' }, 5000)
}

// ── 向量索引 ──────────────────────────────────────────
const stats = reactive<IndexStats>({ software_count: 0, workspace_count: 0 })
const reindexing = ref(false)
const reindexMsg = ref('')

async function loadStats() {
  try {
    const { data } = await getIndexStats()
    stats.software_count = data.software_count
    stats.workspace_count = data.workspace_count
  } catch { /* ignore */ }
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

// ── 扫描导入 ──────────────────────────────────────────
const scanningApps = ref(false)
const scanAppsResult = ref<ScanDirsResponse | null>(null)
const scanningWs = ref(false)
const scanWsResult = ref<WorkspaceScanResponse | null>(null)

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

// ── 端口配置 ──────────────────────────────────────────
const portForm = reactive({ port: 8147, currentPort: 8147 })
const savingPort = ref(false)
const portMsg = ref('')
const portMsgType = ref<'success' | 'error'>('success')

async function loadPortConfig() {
  try {
    const { data } = await getPortConfig()
    portForm.port = data.configured_port
    portForm.currentPort = data.current_port
  } catch { /* ignore */ }
}

async function savePort() {
  if (portForm.port < 1024 || portForm.port > 65535) {
    portMsg.value = '端口号必须在 1024-65535 之间'
    portMsgType.value = 'error'
    return
  }
  savingPort.value = true
  portMsg.value = ''
  try {
    const { data } = await updatePortConfig(portForm.port)
    portMsg.value = data.message
    portMsgType.value = 'success'
    setTimeout(() => { portMsg.value = '' }, 5000)
  } catch {
    portMsg.value = '保存失败'
    portMsgType.value = 'error'
  } finally {
    savingPort.value = false
  }
}

// ── 配置导入导出 ──────────────────────────────────────
const configIoMsg = ref('')
const configIoMsgType = ref<'success' | 'error'>('success')

async function exportConfig() {
  try {
    const { data } = await exportSettings()
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `linkhub-config-${new Date().toISOString().slice(0, 19).replace(/[T:]/g, '-')}.json`
    a.click()
    URL.revokeObjectURL(url)
    configIoMsg.value = '配置已导出'
    configIoMsgType.value = 'success'
    setTimeout(() => { configIoMsg.value = '' }, 3000)
  } catch {
    configIoMsg.value = '导出失败'
    configIoMsgType.value = 'error'
  }
}

async function importConfig(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return

  try {
    const text = await file.text()
    let config: Record<string, unknown>
    try {
      config = JSON.parse(text)
    } catch {
      configIoMsg.value = '导入失败：JSON 格式解析错误'
      configIoMsgType.value = 'error'
      return
    }

    if (typeof config !== 'object' || config === null || Array.isArray(config)) {
      configIoMsg.value = '导入失败：配置文件应为 JSON 对象'
      configIoMsgType.value = 'error'
      return
    }

    // 兼容旧版: allowed_dirs 可能是字符串数组
    if (Array.isArray(config.allowed_dirs)) {
      config.allowed_dirs = (config.allowed_dirs as Array<unknown>).map((item) => {
        if (typeof item === 'string') return { path: item, type: 'software' }
        return item
      })
    }

    const { data } = await importSettings(config)
    configIoMsg.value = `${data.message}，正在重新加载...`
    configIoMsgType.value = 'success'
    // 重新加载所有数据
    await Promise.all([loadAllowedDirs(), loadConfig(), loadStats(), loadPortConfig()])
    configIoMsg.value = `配置导入完成 (${data.imported_keys.length} 项)`
    setTimeout(() => { configIoMsg.value = '' }, 5000)
  } catch {
    configIoMsg.value = '导入失败：请检查文件内容'
    configIoMsgType.value = 'error'
  } finally {
    input.value = '' // 允许重复选择同一文件
  }
}

// ── 服务管理 ─────────────────────────────────────────
const shuttingDown = ref(false)
const shutdownMsg = ref('')

async function confirmShutdown() {
  const result = await confirmRef.value?.confirm({
    title: '关闭服务',
    message: '确定要关闭 LinkHub 服务吗？关闭后需要重新启动程序才能使用。',
    buttons: [
      { label: '取消', value: 'cancel', class: 'text-gray-600 bg-gray-100 hover:bg-gray-200 focus:ring-gray-400' },
      { label: '关闭服务', value: 'ok', class: 'text-white bg-red-600 hover:bg-red-700 focus:ring-red-500' },
    ],
  })
  if (result !== 'ok') return
  shuttingDown.value = true
  shutdownMsg.value = ''
  try {
    await shutdownServer()
    shutdownMsg.value = '服务正在关闭，页面即将失去连接...'
  } catch {
    shutdownMsg.value = '服务已关闭'
  }
}

// ── 版本信息 ─────────────────────────────────────────
const appVersion = ref('')

async function loadVersion() {
  try {
    const { data } = await getHealth()
    appVersion.value = data.version ? `v${data.version}` : ''
  } catch { /* ignore */ }
}

// ── 初始化 ───────────────────────────────────────────
onMounted(() => {
  loadAllowedDirs()
  loadConfig()
  loadStats()
  loadPortConfig()
  loadVersion()
  loadBlacklistCards()
  document.addEventListener('click', closeBlacklistDropdowns)
})

onBeforeUnmount(() => {
  document.removeEventListener('click', closeBlacklistDropdowns)
})
</script>
