<template>
  <div>
    <!-- SoftwareCard: 软件卡片组件 -->
    <div
      :data-id="software.id"
      class="bg-white rounded-xl border shadow-sm overflow-hidden transition-all hover:shadow-md"
      :class="software.is_missing ? 'border-gray-300 opacity-60' : isResourceOnly ? 'border-amber-200' : 'border-gray-200'"
    >
      <div class="p-4">
        <!-- 标题行 -->
        <div class="flex items-start justify-between gap-2 mb-2">
          <div class="flex items-center gap-2 min-w-0 flex-1">
            <!-- 多选复选框 -->
            <input
              v-if="selectable"
              type="checkbox"
              :checked="selected"
              class="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500 flex-shrink-0 cursor-pointer"
              @change="$emit('toggle-select', software.id)"
            />
            <span v-if="!iconData" class="text-lg flex-shrink-0">
              {{ software.is_missing ? '⚠️' : isResourceOnly ? '📁' : '📦' }}
            </span>
            <img
              v-else
              :src="'data:image/png;base64,' + iconData"
              class="w-5 h-5 flex-shrink-0 object-contain"
              alt="icon"
            />
            <h3
              class="text-sm font-semibold truncate"
              :class="software.is_missing ? 'text-gray-400 line-through' : 'text-gray-900'"
              :title="software.name"
            >
              {{ software.name }}
            </h3>
          </div>

          <!-- 操作菜单 -->
          <div class="flex items-center gap-1 flex-shrink-0">
            <!-- 正常软件：启动按钮 -->
            <button
              v-if="!software.is_missing && !isResourceOnly && software.executable_path"
              class="p-1.5 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
              title="启动"
              @click="$emit('launch', software.executable_path)"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </button>
            <!-- 资源类：打开目录按钮（突出显示） -->
            <button
              v-if="isResourceOnly"
              class="p-1.5 text-amber-600 hover:bg-amber-50 rounded-lg transition-colors"
              title="打开目录"
              @click="$emit('open-dir', folderPath)"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 19a2 2 0 01-2-2V7a2 2 0 012-2h4l2 2h4a2 2 0 012 2v1M5 19h14a2 2 0 002-2v-5a2 2 0 00-2-2H9a2 2 0 00-2 2v5a2 2 0 01-2 2z" />
              </svg>
            </button>
            <button
              class="p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
              title="删除"
              @click="$emit('delete', software.id)"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
            </button>
          </div>
        </div>

        <!-- 描述区域 -->
        <div class="mb-3">
          <!-- 编辑模式 -->
          <div v-if="isEditing" class="space-y-2">
            <textarea
              ref="editTextarea"
              v-model="editDescription"
              class="w-full text-xs text-gray-700 border border-gray-300 rounded-lg p-2 resize-none focus:outline-none focus:ring-1 focus:ring-blue-400 focus:border-blue-400"
              rows="3"
              placeholder="输入软件描述..."
            />
            <div class="flex items-center gap-1.5 justify-end">
              <button
                class="px-2 py-1 text-[11px] text-gray-500 hover:text-gray-700 rounded transition-colors"
                @click="cancelEdit"
              >
                取消
              </button>
              <button
                class="px-2 py-1 text-[11px] text-white bg-blue-500 hover:bg-blue-600 rounded transition-colors"
                @click="saveEdit"
              >
                保存
              </button>
            </div>
          </div>

          <!-- 显示模式 -->
          <div v-else>
            <p
              v-if="software.description"
              class="text-xs text-gray-500 line-clamp-2"
            >
              {{ software.description }}
            </p>
            <p v-else class="text-xs text-gray-300 italic">暂无描述</p>

            <!-- 描述操作按钮 -->
            <div class="flex items-center gap-1 mt-1.5">
              <button
                class="p-1 text-gray-300 hover:text-purple-500 hover:bg-purple-50 rounded transition-colors"
                :class="generating ? 'animate-pulse text-purple-400' : ''"
                :title="generating ? '生成中...' : 'AI 生成描述'"
                :disabled="generating"
                @click="handleGenerate"
              >
                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456z" />
                </svg>
              </button>
              <button
                class="p-1 text-gray-300 hover:text-blue-500 hover:bg-blue-50 rounded transition-colors"
                title="编辑描述"
                @click="startEdit"
              >
                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931z" />
                </svg>
              </button>
              <button
                v-if="software.executable_path || software.install_dir"
                class="p-1 text-gray-300 hover:text-blue-600 hover:bg-blue-50 rounded transition-colors"
                title="打开所在文件夹"
                @click="$emit('open-dir', folderPath)"
              >
                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 19a2 2 0 01-2-2V7a2 2 0 012-2h4l2 2h4a2 2 0 012 2v1M5 19h14a2 2 0 002-2v-5a2 2 0 00-2-2H9a2 2 0 00-2 2v5a2 2 0 01-2 2z" />
                </svg>
              </button>
            </div>
          </div>
        </div>

        <!-- 路径 -->
        <div class="text-[11px] text-gray-400 font-mono truncate" :title="software.executable_path">
          {{ software.executable_path || '未指定可执行文件' }}
        </div>

        <!-- 状态标记 -->
        <div v-if="software.is_missing || isResourceOnly" class="mt-2">
          <span
            v-if="software.is_missing"
            class="inline-block text-[10px] px-2 py-0.5 bg-red-50 text-red-600 rounded-full font-medium"
          >
            路径失效
          </span>
          <span
            v-else-if="isResourceOnly"
            class="inline-block text-[10px] px-2 py-0.5 bg-amber-50 text-amber-600 rounded-full font-medium"
          >
            资源
          </span>
        </div>

        <!-- 标签 -->
        <div v-if="parsedTags.length > 0" class="flex flex-wrap gap-1 mt-2">
          <span
            v-for="tag in parsedTags"
            :key="tag"
            class="text-[10px] px-1.5 py-0.5 bg-gray-100 text-gray-600 rounded"
          >
            {{ tag }}
          </span>
        </div>
      </div>
    </div>
  </div>

  <!-- AI Prompt 弹窗 -->
  <AiPromptDialog
    v-if="showAiDialog"
    @cancel="showAiDialog = false"
    @confirm="doGenerate"
  />
</template>

<script setup lang="ts">
import { ref, computed, nextTick, onMounted } from 'vue'
import type { Software } from '@/api'
import { generateSoftwareDescription, updateSoftware, extractIcon } from '@/api'
import AiPromptDialog from '@/components/AiPromptDialog.vue'

const props = defineProps<{
  software: Software
  selectable?: boolean
  selected?: boolean
}>()

const emit = defineEmits<{
  launch: [path: string]
  delete: [id: string]
  updated: [software: Software]
  'toggle-select': [id: string]
  'open-dir': [path: string]
}>()

// 描述编辑状态
const isEditing = ref(false)
const editDescription = ref('')
const editTextarea = ref<HTMLTextAreaElement | null>(null)

// LLM 生成状态
const generating = ref(false)
const showAiDialog = ref(false)

// 资源类判断：exe不存在但目录存在
const isResourceOnly = computed(() => {
  return props.software.exe_exists === false && props.software.dir_exists === true
})

// 图标数据
const iconData = ref<string | null>(null)

// 加载 exe 图标
async function loadIcon() {
  if (!props.software.executable_path || props.software.is_missing || isResourceOnly.value) return
  try {
    const { data } = await extractIcon(props.software.executable_path, 32)
    if (data.success && data.icon_base64) {
      iconData.value = data.icon_base64
    }
  } catch {
    // 图标加载失败，使用默认 emoji
  }
}

onMounted(() => {
  loadIcon()
})

const parentDir = computed(() => {
  if (!props.software.executable_path) return ''
  // Windows paths use backslash; take parent directory of the exe
  const sep = props.software.executable_path.includes('\\') ? '\\' : '/'
  const parts = props.software.executable_path.split(sep)
  parts.pop() // remove filename
  return parts.join(sep)
})

const folderPath = computed(() => {
  // Prefer parent dir of executable_path, fallback to install_dir
  if (parentDir.value) return parentDir.value
  return props.software.install_dir || ''
})

const parsedTags = computed(() => {
  if (!props.software.tags) return []
  try {
    const arr = JSON.parse(props.software.tags)
    return Array.isArray(arr) ? arr : []
  } catch {
    return []
  }
})

function startEdit() {
  editDescription.value = props.software.description || ''
  isEditing.value = true
  nextTick(() => editTextarea.value?.focus())
}

function cancelEdit() {
  isEditing.value = false
  editDescription.value = ''
}

async function saveEdit() {
  try {
    const { data } = await updateSoftware(props.software.id, {
      description: editDescription.value || null,
    })
    emit('updated', data)
    isEditing.value = false
  } catch {
    alert('保存失败，请重试')
  }
}

async function handleGenerate() {
  if (generating.value) return
  showAiDialog.value = true
}

async function doGenerate(payload: { customPrompt: string; mode: 'append' | 'override' }) {
  showAiDialog.value = false
  generating.value = true
  try {
    const { data } = await generateSoftwareDescription(
      props.software.id,
      payload.customPrompt || undefined,
      payload.mode,
    )
    if (data.success) {
      emit('updated', { ...props.software, description: data.description })
    } else {
      alert(data.message || '生成失败')
    }
  } catch (e: unknown) {
    const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '生成失败，请检查 LLM 配置'
    alert(detail)
  } finally {
    generating.value = false
  }
}
</script>
