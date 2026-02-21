<template>
  <!-- 弹窗遮罩 -->
  <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/40" @click.self="$emit('close')">
    <div class="bg-white rounded-xl shadow-xl w-full max-w-md mx-4 p-6">
      <h3 class="text-lg font-bold text-gray-900 mb-5">
        {{ isEdit ? '编辑工作区' : '新建工作区' }}
      </h3>

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
        </div>

        <!-- 目录路径 -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">目录路径</label>
          <input
            v-model="form.directory_path"
            type="text"
            placeholder="例: C:\Projects\MyProject"
            class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent font-mono"
          />
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
          <input
            v-model="form.deadline"
            type="date"
            class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
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
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { createWorkspace, updateWorkspace, generateWorkspaceDescription } from '@/api'
import type { Workspace } from '@/api'

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

const saving = ref(false)
const error = ref('')
const generatingDesc = ref(false)

onMounted(() => {
  if (props.workspace) {
    form.name = props.workspace.name
    form.directory_path = props.workspace.directory_path
    form.description = props.workspace.description || ''
    form.deadline = props.workspace.deadline
      ? new Date(props.workspace.deadline).toISOString().split('T')[0]
      : ''
    form.status = props.workspace.status
  }
})

async function handleGenerateDescription() {
  if (!props.workspace || generatingDesc.value) return
  generatingDesc.value = true
  error.value = ''
  try {
    const { data } = await generateWorkspaceDescription(props.workspace.id)
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

async function save() {
  error.value = ''

  if (!form.name.trim()) { error.value = '名称不能为空'; return }
  if (!form.directory_path.trim()) { error.value = '目录路径不能为空'; return }

  saving.value = true
  try {
    const payload: Record<string, unknown> = {
      name: form.name.trim(),
      directory_path: form.directory_path.trim(),
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
