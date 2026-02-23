<template>
  <div class="relative" ref="comboRef">
    <div class="relative">
      <input
        v-model="inputValue"
        type="text"
        :placeholder="placeholder"
        class="w-full px-3 py-2 pr-8 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
        @focus="showDropdown = true"
        @input="onInput"
      />
      <button
        type="button"
        class="absolute right-1.5 top-1/2 -translate-y-1/2 p-1 text-gray-400 hover:text-gray-600"
        @click="toggleDropdown"
      >
        <ChevronDown :size="16" class="transition-transform" :class="{ 'rotate-180': showDropdown }" />
      </button>
    </div>

    <!-- 下拉列表 -->
    <div
      v-if="showDropdown && filteredOptions.length > 0"
      class="absolute z-50 w-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg max-h-56 overflow-y-auto"
    >
      <button
        v-for="opt in filteredOptions"
        :key="opt.value"
        type="button"
        class="w-full px-3 py-2 text-left text-sm hover:bg-blue-50 transition-colors flex items-center justify-between gap-2"
        :class="{ 'bg-blue-50 text-blue-700': opt.value === modelValue }"
        @mousedown.prevent="selectOption(opt)"
      >
        <div class="min-w-0">
          <div class="font-medium text-gray-800 truncate">{{ opt.label }}</div>
          <div class="text-xs text-gray-400 truncate">{{ opt.value }}</div>
        </div>
        <Check v-if="opt.value === modelValue" :size="16" class="shrink-0 text-blue-500" />
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { ChevronDown, Check } from 'lucide-vue-next'

export interface ComboOption {
  label: string
  value: string
}

const props = defineProps<{
  modelValue: string
  options: ComboOption[]
  placeholder?: string
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
}>()

const inputValue = ref(props.modelValue)
const showDropdown = ref(false)
const comboRef = ref<HTMLElement | null>(null)

watch(() => props.modelValue, (v) => {
  inputValue.value = v
})

const filteredOptions = computed(() => {
  const q = inputValue.value.toLowerCase().trim()
  if (!q) return props.options
  return props.options.filter(
    opt => opt.label.toLowerCase().includes(q) || opt.value.toLowerCase().includes(q)
  )
})

function onInput() {
  showDropdown.value = true
  emit('update:modelValue', inputValue.value)
}

function selectOption(opt: ComboOption) {
  inputValue.value = opt.value
  emit('update:modelValue', opt.value)
  showDropdown.value = false
}

function toggleDropdown() {
  showDropdown.value = !showDropdown.value
}

function onClickOutside(e: MouseEvent) {
  if (comboRef.value && !comboRef.value.contains(e.target as Node)) {
    showDropdown.value = false
  }
}

onMounted(() => document.addEventListener('mousedown', onClickOutside))
onUnmounted(() => document.removeEventListener('mousedown', onClickOutside))
</script>
