<template>
  <Teleport to="body">
    <div
      v-if="visible"
      class="fixed inset-0 z-[9999]"
      @click="close"
      @contextmenu.prevent="close"
    >
      <div
        ref="menuRef"
        class="absolute bg-white rounded-lg shadow-lg border border-gray-200 py-1 min-w-[160px] z-[10000] animate-in"
        :style="{ top: posY + 'px', left: posX + 'px' }"
      >
        <template v-for="(item, idx) in items" :key="idx">
          <!-- 分割线 -->
          <div v-if="item.separator" class="my-1 border-t border-gray-100" />
          <!-- 菜单项 -->
          <button
            v-else
            class="w-full flex items-center gap-2 px-3 py-1.5 text-xs transition-colors text-left"
            :class="item.danger
              ? 'text-red-600 hover:bg-red-50'
              : item.disabled
                ? 'text-gray-300 cursor-not-allowed'
                : 'text-gray-700 hover:bg-gray-100'"
            :disabled="item.disabled"
            @click.stop="handleClick(item)"
          >
            <component
              v-if="item.icon"
              :is="item.icon"
              :size="14"
              class="flex-shrink-0"
            />
            <span v-if="item.emoji" class="flex-shrink-0 text-sm leading-none">{{ item.emoji }}</span>
            <span>{{ item.label }}</span>
          </button>
        </template>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, nextTick, type Component } from 'vue'

export interface ContextMenuItem {
  label?: string
  icon?: Component
  emoji?: string
  action?: () => void
  danger?: boolean
  disabled?: boolean
  separator?: boolean
}

const props = defineProps<{
  items: ContextMenuItem[]
}>()

const visible = ref(false)
const posX = ref(0)
const posY = ref(0)
const menuRef = ref<HTMLElement | null>(null)

function open(e: MouseEvent) {
  e.preventDefault()
  e.stopPropagation()
  posX.value = e.clientX
  posY.value = e.clientY
  visible.value = true

  // 确保菜单不超出视口
  nextTick(() => {
    if (!menuRef.value) return
    const rect = menuRef.value.getBoundingClientRect()
    const vw = window.innerWidth
    const vh = window.innerHeight
    if (rect.right > vw) {
      posX.value = Math.max(4, e.clientX - rect.width)
    }
    if (rect.bottom > vh) {
      posY.value = Math.max(4, e.clientY - rect.height)
    }
  })
}

function close() {
  visible.value = false
}

function handleClick(item: ContextMenuItem) {
  if (item.disabled) return
  close()
  item.action?.()
}

defineExpose({ open, close })
</script>

<style scoped>
.animate-in {
  animation: ctx-fade-in 0.1s ease-out;
}
@keyframes ctx-fade-in {
  from { opacity: 0; transform: scale(0.95); }
  to { opacity: 1; transform: scale(1); }
}
</style>
