<template>
  <!-- 弹窗遮罩 -->
  <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/40" @click.self="$emit('close')">
    <div class="bg-white rounded-xl shadow-xl w-full max-w-md mx-4 p-6">
      <div class="flex items-center justify-between mb-5">
        <h3 class="text-lg font-bold text-gray-900">
          {{ isEdit ? '编辑工作区' : '新建工作区' }}
        </h3>
        <button
          class="flex items-center gap-1 px-2.5 py-1 text-xs font-medium text-purple-600 hover:bg-purple-50 rounded-lg transition-colors disabled:opacity-50"
          :disabled="aiFilling"
          :title="aiFilling ? 'AI 填充中...' : 'AI 根据目录路径自动填充表单'"
          @click="handleAiFill"
        >
          <svg class="w-3.5 h-3.5" :class="aiFilling ? 'animate-pulse' : ''" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456z" />
          </svg>
          {{ aiFilling ? 'AI 填充中...' : 'AI 填充' }}
        </button>
      </div>

      <div class="space-y-4">
        <!-- 名称 -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">名称</label>
          <input
            v-model="form.name"
            type="text"
            placeholder="项目名称"
            class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
          <p v-if="!isEdit" class="mt-1 text-[11px] text-gray-400">
            支持日期变量: %date%, %yyyy%, %mm%, %dd%
          </p>
        </div>

        <!-- 目录路径 -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">目录路径</label>
          <div class="flex items-center gap-2">
            <input
              v-model="form.directory_path"
              type="text"
              placeholder="例: C:\Projects\MyProject"
              class="flex-1 px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent font-mono"
            />
            <button
              type="button"
              class="p-2 text-gray-400 hover:text-blue-500 transition-colors shrink-0"
              @click="showFolderPicker = true"
              title="浏览..."
            >
              <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
              </svg>
            </button>
          </div>
        </div>

        <!-- 描述 -->
        <div>
          <div class="flex items-center justify-between mb-1">
            <label class="block text-sm font-medium text-gray-700">描述</label>
            <button
              v-if="isEdit && workspace"
              class="flex items-center gap-1 px-2 py-0.5 text-[11px] text-purple-600 hover:bg-purple-50 rounded transition-colors disabled:opacity-50"
              :disabled="generatingDesc"
              :title="generatingDesc ? '生成中...' : 'AI 生成描述'"
              @click="handleGenerateDescription"
            >
              <svg class="w-3.5 h-3.5" :class="generatingDesc ? 'animate-pulse' : ''" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456z" />
              </svg>
              {{ generatingDesc ? '生成中...' : 'AI 生成' }}
            </button>
          </div>
          <textarea
            v-model="form.description"
            rows="2"
            placeholder="简要描述..."
            class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
          />
        </div>

        <!-- 截止日期 -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">截止日期 (可选)</label>
          <div class="relative">
            <DatePicker
              v-model="deadlineDate"
              :masks="{ input: 'YYYY-MM-DD' }"
              :popover="{ visibility: 'focus' }"
              color="blue"
            >
              <template #default="{ inputValue, inputEvents }">
                <div class="flex items-center gap-2">
                  <input
                    :value="inputValue"
                    v-on="inputEvents"
                    type="text"
                    placeholder="选择截止日期"
                    readonly
                    class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent cursor-pointer"
                  />
                  <button
                    v-if="deadlineDate"
                    type="button"
                    class="absolute right-2 p-1 text-gray-400 hover:text-gray-600 transition-colors"
                    title="清除日期"
                    @click="deadlineDate = null"
                  >
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
              </template>
            </DatePicker>
          </div>
        </div>

        <!-- 状态 -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">状态</label>
          <select
            v-model="form.status"
            class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="not_started">未开始</option>
            <option value="active">进行中</option>
            <option value="completed">已完成</option>
            <option value="archived">已归档</option>
          </select>
        </div>
      </div>

      <!-- 错误消息 -->
      <div v-if="error" class="mt-3 p-2 text-xs text-red-600 bg-red-50 rounded-lg">{{ error }}</div>

      <!-- 按钮 -->
      <div class="flex items-center justify-end gap-3 mt-6">
        <button
          class="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
          @click="$emit('close')"
        >
          取消
        </button>
        <button
          class="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
          :disabled="saving"
          @click="save"
        >
          {{ saving ? '保存中...' : '保存' }}
        </button>
      </div>
    </div>
  </div>

  <!-- 文件夹选择器弹窗 -->
  <FolderPickerDialog
    v-if="showFolderPicker"
    :initial-path="form.directory_path"
    @confirm="onFolderPicked"
    @cancel="showFolderPicker = false"
  />

  <!-- AI Prompt 弹窗 -->
  <AiPromptDialog
    v-if="showAiDialog"
    @cancel="showAiDialog = false"
    @confirm="doGenerateDescription"
  />
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { createWorkspace, updateWorkspace, generateWorkspaceDescription, getAllowedDirs, aiWorkspaceFillForm } from '@/api'
import type { Workspace, DirEntry } from '@/api'
import { DatePicker } from 'v-calendar'
import FolderPickerDialog from '@/components/FolderPickerDialog.vue'
import AiPromptDialog from '@/components/AiPromptDialog.vue'

const props = defineProps<{
  workspace: Workspace | null
}>()

const emit = defineEmits<{
  close: []
  saved: []
}>()

const isEdit = computed(() => !!props.workspace)

const form = reactive({
  name: '',
  directory_path: '',
  description: '',
  deadline: '',
  status: 'active',
})

// VCalendar 使用 Date 对象，form.deadline 使用 YYYY-MM-DD 字符串
const deadlineDate = ref<Date | null>(null)

// 同步 Date 对象 → form.deadline 字符串
watch(deadlineDate, (d) => {
  if (d) {
    const yyyy = d.getFullYear()
    const mm = String(d.getMonth() + 1).padStart(2, '0')
    const dd = String(d.getDate()).padStart(2, '0')
    form.deadline = `${yyyy}-${mm}-${dd}`
  } else {
    form.deadline = ''
  }
})

const saving = ref(false)
const error = ref('')
const generatingDesc = ref(false)
const aiFilling = ref(false)
const showFolderPicker = ref(false)
const showAiDialog = ref(false)

// 工作区白名单目录（用于自动补全路径）
const workspaceDirs = ref<string[]>([])

onMounted(async () => {
  if (props.workspace) {
    form.name = props.workspace.name
    form.directory_path = props.workspace.directory_path
    form.description = props.workspace.description || ''
    if (props.workspace.deadline) {
      const parsed = new Date(props.workspace.deadline)
      if (!isNaN(parsed.getTime())) {
        deadlineDate.value = parsed
      }
    }
    form.status = props.workspace.status
  }

  // 加载白名单目录
  try {
    const { data } = await getAllowedDirs()
    workspaceDirs.value = data.allowed_dirs
      .filter((d: DirEntry) => d.type === 'workspace')
      .map((d: DirEntry) => d.path.replace(/\/$/, '').replace(/\\$/, ''))
  } catch { /* ignore */ }
})

// 新建模式下：name 变化时自动拼接路径
watch(() => form.name, (newName) => {
  if (isEdit.value) return
  if (!newName.trim()) return
  // 仅当路径为空或路径等于某个白名单目录（未手动修改过）时，才自动补全
  const trimmedPath = form.directory_path.replace(/[\\/]$/, '')
  const isBaseDir = !trimmedPath || workspaceDirs.value.includes(trimmedPath)
  if (isBaseDir && workspaceDirs.value.length > 0) {
    const sep = workspaceDirs.value[0].includes('/') ? '/' : '\\'
    form.directory_path = workspaceDirs.value[0] + sep + newName.trim()
  }
})

/**
 * 日期转义: 将 %date%, %yyyy%, %mm%, %dd% 等替换为实际日期
 */
function escapeDateTokens(str: string): string {
  const now = new Date()
  const yyyy = String(now.getFullYear())
  const mm = String(now.getMonth() + 1).padStart(2, '0')
  const dd = String(now.getDate()).padStart(2, '0')
  return str
    .replace(/%date%/gi, `${yyyy}-${mm}-${dd}`)
    .replace(/%yyyy%/gi, yyyy)
    .replace(/%mm%/gi, mm)
    .replace(/%dd%/gi, dd)
}

function onFolderPicked(path: string) {
  form.directory_path = path
  showFolderPicker.value = false
}

async function handleGenerateDescription() {
  if (!props.workspace || generatingDesc.value) return
  showAiDialog.value = true
}

async function doGenerateDescription(payload: { customPrompt: string; mode: 'append' | 'override' }) {
  if (!props.workspace) return
  showAiDialog.value = false
  generatingDesc.value = true
  error.value = ''
  try {
    const { data } = await generateWorkspaceDescription(
      props.workspace.id,
      payload.customPrompt || undefined,
      payload.mode,
    )
    if (data.success) {
      form.description = data.description
    } else {
      error.value = data.message || '描述生成失败'
    }
  } catch (e: unknown) {
    const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '生成失败，请检查 LLM 配置'
    error.value = typeof detail === 'string' ? detail : JSON.stringify(detail)
  } finally {
    generatingDesc.value = false
  }
}

async function handleAiFill() {
  if (aiFilling.value) return
  if (!form.directory_path.trim()) {
    error.value = '请先填写目录路径，AI 需要根据目录路径推断表单内容'
    return
  }
  aiFilling.value = true
  error.value = ''
  try {
    const { data } = await aiWorkspaceFillForm(form.directory_path.trim())
    if (data.success) {
      if (data.name) form.name = data.name
      if (data.description) form.description = data.description
      if (data.deadline) {
        const parsed = new Date(data.deadline)
        if (!isNaN(parsed.getTime())) {
          deadlineDate.value = parsed
        }
      }
    } else {
      error.value = data.message || 'AI 填充失败'
    }
  } catch (e: unknown) {
    const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'AI 填充失败，请检查 LLM 配置'
    error.value = typeof detail === 'string' ? detail : JSON.stringify(detail)
  } finally {
    aiFilling.value = false
  }
}

async function save() {
  error.value = ''

  if (!form.name.trim()) { error.value = '名称不能为空'; return }
  if (!form.directory_path.trim()) { error.value = '目录路径不能为空'; return }

  saving.value = true
  try {
    const payload: Record<string, unknown> = {
      name: escapeDateTokens(form.name.trim()),
      directory_path: escapeDateTokens(form.directory_path.trim()),
      description: form.description.trim() || null,
      status: form.status,
    }
    if (form.deadline) {
      payload.deadline = form.deadline + 'T00:00:00'
    } else {
      payload.deadline = null
    }

    if (isEdit.value && props.workspace) {
      await updateWorkspace(props.workspace.id, payload)
    } else {
      await createWorkspace(payload)
    }
    emit('saved')
  } catch (e: unknown) {
    const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '保存失败'
    error.value = typeof detail === 'string' ? detail : JSON.stringify(detail)
  } finally {
    saving.value = false
  }
}
</script>
