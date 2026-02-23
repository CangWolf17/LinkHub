<template>
  <div class="text-xs font-mono">
    <!-- 加载状态 -->
    <div v-if="loading" class="flex items-center gap-2 py-2 text-gray-400">
      <Loader2 :size="14" class="animate-spin" />
      <span>加载中...</span>
    </div>

    <!-- 错误状态 -->
    <div v-else-if="errorMsg" class="py-2 text-red-500">{{ errorMsg }}</div>

    <!-- 空目录 -->
    <div v-else-if="items.length === 0" class="py-2 text-gray-400 italic">空目录</div>

    <!-- 目录内容 -->
    <div v-else class="space-y-0">
      <DirectoryTreeNode
        v-for="item in items"
        :key="item.path"
        :item="item"
        :depth="0"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { listDir } from '@/api'
import type { ListDirItem } from '@/api'
import DirectoryTreeNode from '@/components/DirectoryTreeNode.vue'
import { Loader2 } from 'lucide-vue-next'

const props = defineProps<{
  rootPath: string
}>()

const items = ref<ListDirItem[]>([])
const loading = ref(false)
const errorMsg = ref('')

async function loadRoot() {
  loading.value = true
  errorMsg.value = ''
  try {
    const { data } = await listDir(props.rootPath)
    if (data.success) {
      items.value = data.items
    } else {
      errorMsg.value = data.message || '无法加载目录'
    }
  } catch {
    errorMsg.value = '加载目录失败'
  } finally {
    loading.value = false
  }
}

onMounted(loadRoot)
</script>
