<template>
  <div>
    <!-- SoftwareCard: 软件卡片组件 -->
    <div
      class="bg-white rounded-xl border shadow-sm overflow-hidden transition-all hover:shadow-md"
      :class="software.is_missing ? 'border-gray-300 opacity-60' : 'border-gray-200'"
    >
      <div class="p-4">
        <!-- 标题行 -->
        <div class="flex items-start justify-between gap-2 mb-2">
          <div class="flex items-center gap-2 min-w-0 flex-1">
            <span class="text-lg flex-shrink-0">
              {{ software.is_missing ? '⚠️' : '📦' }}
            </span>
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
            <button
              v-if="!software.is_missing && software.executable_path"
              class="p-1.5 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
              title="启动"
              @click="$emit('launch', software.executable_path)"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
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

        <!-- 描述 -->
        <p
          v-if="software.description"
          class="text-xs text-gray-500 mb-3 line-clamp-2"
        >
          {{ software.description }}
        </p>

        <!-- 路径 -->
        <div class="text-[11px] text-gray-400 font-mono truncate" :title="software.executable_path">
          {{ software.executable_path || '未指定可执行文件' }}
        </div>

        <!-- 死链标记 -->
        <div v-if="software.is_missing" class="mt-2">
          <span class="inline-block text-[10px] px-2 py-0.5 bg-red-50 text-red-600 rounded-full font-medium">
            路径失效
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
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { Software } from '@/api'

const props = defineProps<{
  software: Software
}>()

defineEmits<{
  launch: [path: string]
  delete: [id: string]
}>()

const parsedTags = computed(() => {
  if (!props.software.tags) return []
  try {
    const arr = JSON.parse(props.software.tags)
    return Array.isArray(arr) ? arr : []
  } catch {
    return []
  }
})
</script>
