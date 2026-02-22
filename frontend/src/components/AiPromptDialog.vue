<template>
  <!-- AI 描述生成弹窗 -->
  <div class="fixed inset-0 z-[60] flex items-center justify-center bg-black/40" @click.self="$emit('cancel')">
    <div class="bg-white rounded-xl shadow-xl w-full max-w-sm mx-4 p-5">
      <h3 class="text-sm font-bold text-gray-900 mb-3">AI 生成描述</h3>

      <!-- 自定义 prompt 输入 -->
      <div class="mb-3">
        <label class="block text-xs text-gray-500 mb-1">自定义要求 (可选)</label>
        <textarea
          v-model="customPrompt"
          rows="2"
          placeholder="例: 用英文描述、侧重技术栈、控制在50字以内..."
          class="w-full px-3 py-2 text-xs border border-gray-300 rounded-lg focus:outline-none focus:ring-1 focus:ring-purple-400 focus:border-purple-400 resize-none"
        />
      </div>

      <!-- prompt 模式选择 -->
      <div v-if="customPrompt.trim()" class="mb-4">
        <label class="block text-xs text-gray-500 mb-1.5">Prompt 模式</label>
        <div class="flex gap-3">
          <label class="flex items-center gap-1.5 text-xs text-gray-700 cursor-pointer">
            <input v-model="mode" type="radio" value="append" class="text-purple-600 focus:ring-purple-500" />
            <span>追加</span>
            <span class="text-gray-400">— 在系统提示词后附加你的要求</span>
          </label>
        </div>
        <div class="flex gap-3 mt-1.5">
          <label class="flex items-center gap-1.5 text-xs text-gray-700 cursor-pointer">
            <input v-model="mode" type="radio" value="override" class="text-purple-600 focus:ring-purple-500" />
            <span>覆盖</span>
            <span class="text-gray-400">— 完全替换系统提示词</span>
          </label>
        </div>
      </div>

      <!-- 按钮 -->
      <div class="flex items-center justify-end gap-2">
        <button
          class="px-3 py-1.5 text-xs font-medium text-gray-600 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
          @click="$emit('cancel')"
        >
          取消
        </button>
        <button
          class="px-3 py-1.5 text-xs font-medium text-white bg-purple-600 rounded-lg hover:bg-purple-700 transition-colors"
          @click="handleConfirm"
        >
          生成
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const emit = defineEmits<{
  cancel: []
  confirm: [payload: { customPrompt: string; mode: 'append' | 'override' }]
}>()

const customPrompt = ref('')
const mode = ref<'append' | 'override'>('append')

function handleConfirm() {
  emit('confirm', {
    customPrompt: customPrompt.value.trim(),
    mode: mode.value,
  })
}
</script>
