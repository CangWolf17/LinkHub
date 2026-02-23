<template>
  <div class="relative">
    <div class="relative">
      <svg
        class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400"
        fill="none" stroke="currentColor" viewBox="0 0 24 24"
      >
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
          d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
      </svg>
      <input
        v-model="query"
        type="text"
        placeholder="语义搜索... (输入自然语言查找软件或工作区)"
        class="w-full pl-10 pr-4 py-2 text-sm bg-gray-50 border border-gray-200 rounded-lg
               focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent
               placeholder-gray-400 transition-all"
        @keydown.enter="doSearch"
        @input="onInput"
      />
      <button
        v-if="query"
        class="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 p-1"
        @click="clearSearch"
      >
        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    </div>

    <!-- 搜索结果下拉 -->
    <div
      v-if="showResults"
      class="absolute top-full left-0 right-0 mt-1 bg-white rounded-lg shadow-lg border border-gray-200 max-h-96 overflow-y-auto z-50"
    >
      <div v-if="loading" class="p-4 text-center text-sm text-gray-500">
        搜索中...
      </div>
      <div v-else-if="results.length === 0 && hasSearched" class="p-4 text-center text-sm text-gray-500">
        未找到相关结果
      </div>
      <div v-else>
        <div
          v-for="item in results"
          :key="item.id"
          class="px-4 py-3 hover:bg-gray-50 cursor-pointer border-b border-gray-100 last:border-0 transition-colors"
          @click="onResultClick(item)"
        >
          <div class="flex items-center gap-2">
            <span class="text-xs px-1.5 py-0.5 rounded font-medium"
              :class="item.type === 'software' ? 'bg-blue-100 text-blue-700' : 'bg-purple-100 text-purple-700'"
            >
              {{ item.type === 'software' ? '软件' : '工作区' }}
            </span>
            <span class="text-sm font-medium text-gray-900" :class="{ 'line-through opacity-50': item.is_missing }">
              {{ item.name }}
            </span>
            <span v-if="item.is_missing" class="text-xs text-red-500">(路径失效)</span>
          </div>
          <p v-if="item.description" class="text-xs text-gray-500 mt-1 line-clamp-1">{{ item.description }}</p>
        </div>
      </div>
    </div>

    <!-- 点击外部关闭 -->
    <div v-if="showResults" class="fixed inset-0 z-40" @click="showResults = false" />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { semanticSearch } from '@/api'
import type { SearchResultItem } from '@/api'

const router = useRouter()

const query = ref('')
const results = ref<SearchResultItem[]>([])
const showResults = ref(false)
const loading = ref(false)
const hasSearched = ref(false)

let debounceTimer: ReturnType<typeof setTimeout> | null = null

function onInput() {
  if (debounceTimer) clearTimeout(debounceTimer)
  if (!query.value.trim()) {
    showResults.value = false
    results.value = []
    hasSearched.value = false
    return
  }
  debounceTimer = setTimeout(doSearch, 400)
}

async function doSearch() {
  const q = query.value.trim()
  if (!q) return

  loading.value = true
  showResults.value = true
  hasSearched.value = true

  try {
    const { data } = await semanticSearch(q, 10, 'all')
    results.value = data.results
  } catch {
    results.value = []
  } finally {
    loading.value = false
  }
}

function clearSearch() {
  query.value = ''
  results.value = []
  showResults.value = false
  hasSearched.value = false
}

function onResultClick(item: SearchResultItem) {
  showResults.value = false
  query.value = ''
  results.value = []
  hasSearched.value = false

  const targetRoute = item.type === 'software' ? '/software' : '/workspaces'
  router.push({ path: targetRoute, query: { highlight: item.id } })
}
</script>
