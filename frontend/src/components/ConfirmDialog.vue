<template>
  <Teleport to="body">
    <transition
      enter-active-class="transition-opacity duration-150 ease-out"
      enter-from-class="opacity-0"
      enter-to-class="opacity-100"
      leave-active-class="transition-opacity duration-100 ease-in"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <div
        v-if="visible"
        class="fixed inset-0 z-[9998] flex items-center justify-center bg-black/40"
        @click.self="handleCancel"
      >
        <div class="bg-white rounded-2xl shadow-xl w-full max-w-sm mx-4 overflow-hidden animate-in">
          <!-- 内容区 -->
          <div class="px-6 pt-6 pb-4">
            <h3 class="text-base font-semibold text-gray-900 mb-2">{{ title }}</h3>
            <p class="text-sm text-gray-600 leading-relaxed whitespace-pre-line">{{ message }}</p>
          </div>
          <!-- 按钮区 -->
          <div class="flex justify-end gap-2 px-6 pb-5">
            <button
              v-for="(btn, idx) in buttons"
              :key="idx"
              class="px-4 py-2 text-sm font-medium rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-offset-1"
              :class="btn.class"
              @click="handleAction(btn.value)"
            >
              {{ btn.label }}
            </button>
          </div>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref } from 'vue'

export interface ConfirmButton {
  label: string
  value: string
  class: string
}

const visible = ref(false)
const title = ref('')
const message = ref('')
const buttons = ref<ConfirmButton[]>([])
let _resolve: ((value: string) => void) | null = null

function confirm(opts: {
  title: string
  message: string
  buttons?: ConfirmButton[]
}): Promise<string> {
  title.value = opts.title
  message.value = opts.message
  buttons.value = opts.buttons || [
    { label: '取消', value: 'cancel', class: 'text-gray-600 bg-gray-100 hover:bg-gray-200 focus:ring-gray-400' },
    { label: '确定', value: 'ok', class: 'text-white bg-blue-600 hover:bg-blue-700 focus:ring-blue-500' },
  ]
  visible.value = true

  return new Promise((resolve) => {
    _resolve = resolve
  })
}

function handleAction(value: string) {
  visible.value = false
  _resolve?.(value)
  _resolve = null
}

function handleCancel() {
  visible.value = false
  _resolve?.('cancel')
  _resolve = null
}

defineExpose({ confirm })
</script>

<style scoped>
.animate-in {
  animation: dialog-scale-in 0.15s ease-out;
}
@keyframes dialog-scale-in {
  from { opacity: 0; transform: scale(0.95) translateY(8px); }
  to { opacity: 1; transform: scale(1) translateY(0); }
}
</style>
