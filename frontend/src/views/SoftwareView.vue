<template>
  <div>
    <div class="flex items-center justify-between mb-6">
      <h2 class="text-xl font-bold text-gray-900">软件舱</h2>
      <div class="flex items-center gap-2">
        <button
          v-if="itemsWithoutDescription.length > 0"
          class="px-3 py-1.5 text-xs font-medium text-purple-600 bg-purple-50 rounded-lg hover:bg-purple-100 transition-colors disabled:opacity-50"
          :disabled="bulkGenerating"
          @click="bulkGenerate"
        >
          {{ bulkGenerating ? `生成中 (${bulkProgress}/${bulkTotal})` : `AI 批量生成描述 (${itemsWithoutDescription.length})` }}
        </button>
        <button
          class="px-3 py-1.5 text-xs font-medium text-red-600 bg-red-50 rounded-lg hover:bg-red-100 transition-colors"
          @click="cleanupDead"
        >
          清理死链
        </button>
      </div>
    </div>

    <!-- 拖拽安装区 -->
    <div
      class="mb-6 border-2 border-dashed rounded-xl p-8 text-center transition-all cursor-pointer"
      :class="[
        isDragging
          ? 'border-blue-500 bg-blue-50'
          : 'border-gray-300 bg-white hover:border-gray-400',
      ]"
      @dragenter.prevent="isDragging = true"
      @dragover.prevent="isDragging = true"
      @dragleave.prevent="isDragging = false"
      @drop.prevent="onDrop"
      @click="triggerFileInput"
    >
      <div v-if="uploading" class="space-y-3">
        <div class="text-sm font-medium text-blue-600">{{ uploadStage }}</div>
        <div class="w-64 mx-auto h-2 bg-gray-200 rounded-full overflow-hidden">
          <div class="h-full bg-blue-500 rounded-full transition-all duration-300" :style="{ width: uploadProgress + '%' }" />
        </div>
        <div class="text-xs text-gray-500">{{ uploadMessage }}</div>
      </div>
      <div v-else>
        <div class="text-3xl mb-2">📦</div>
        <p class="text-sm text-gray-600">
          拖入 <span class="font-medium text-gray-900">.zip</span> 压缩包自动安装，或
          <span class="text-blue-600 underline">点击选择文件</span>
        </p>
        <p class="text-xs text-gray-400 mt-1">支持: 便携软件压缩包 (自动解压 + 启发式寻址 + LLM 描述生成)</p>
      </div>
    </div>

    <input ref="fileInput" type="file" accept=".zip" class="hidden" @change="onFileSelect" />

    <!-- 软件卡片网格 -->
    <div v-if="loading" class="text-center py-12 text-gray-500 text-sm">加载中...</div>
    <div v-else-if="items.length === 0" class="text-center py-12 text-gray-400 text-sm">
      暂无软件记录，拖入压缩包开始安装
    </div>
    <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      <SoftwareCard
        v-for="sw in items"
        :key="sw.id"
        :software="sw"
        @launch="handleLaunch"
        @delete="handleDelete"
        @updated="handleUpdated"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { getSoftwareList, uploadInstall, deleteSoftware, launchApp, cleanupDeadSoftware, generateSoftwareDescription } from '@/api'
import type { Software } from '@/api'
import SoftwareCard from '@/components/SoftwareCard.vue'

const items = ref<Software[]>([])
const loading = ref(true)
const isDragging = ref(false)
const uploading = ref(false)
const uploadStage = ref('')
const uploadProgress = ref(0)
const uploadMessage = ref('')
const fileInput = ref<HTMLInputElement | null>(null)

// 批量生成状态
const bulkGenerating = ref(false)
const bulkProgress = ref(0)
const bulkTotal = ref(0)

const itemsWithoutDescription = computed(() =>
  items.value.filter((s) => !s.description && !s.is_missing)
)

async function loadList() {
  loading.value = true
  try {
    const { data } = await getSoftwareList()
    items.value = data.items
  } catch { /* ignore */ } finally {
    loading.value = false
  }
}

function triggerFileInput() {
  if (uploading.value) return
  fileInput.value?.click()
}

function onFileSelect(e: Event) {
  const target = e.target as HTMLInputElement
  const file = target.files?.[0]
  if (file) doUpload(file)
  target.value = ''
}

function onDrop(e: DragEvent) {
  isDragging.value = false
  const file = e.dataTransfer?.files[0]
  if (file) doUpload(file)
}

async function doUpload(file: File) {
  if (uploading.value) return
  uploading.value = true
  uploadStage.value = '上传中...'
  uploadProgress.value = 20
  uploadMessage.value = file.name

  try {
    uploadStage.value = '解压 + 分析中...'
    uploadProgress.value = 50

    const { data } = await uploadInstall(file)

    uploadStage.value = '安装完成!'
    uploadProgress.value = 100
    uploadMessage.value = data.message

    await new Promise((r) => setTimeout(r, 1500))
    await loadList()
  } catch (e: unknown) {
    const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '安装失败'
    uploadStage.value = '安装失败'
    uploadProgress.value = 0
    uploadMessage.value = detail
    await new Promise((r) => setTimeout(r, 3000))
  } finally {
    uploading.value = false
    uploadStage.value = ''
    uploadProgress.value = 0
    uploadMessage.value = ''
  }
}

async function handleLaunch(path: string) {
  try {
    await launchApp(path)
  } catch (e: unknown) {
    const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '启动失败'
    alert(detail)
  }
}

async function handleDelete(id: string) {
  if (!confirm('确定删除这条记录吗?')) return
  try {
    await deleteSoftware(id)
    items.value = items.value.filter((s) => s.id !== id)
  } catch { /* ignore */ }
}

function handleUpdated(updated: Software) {
  const idx = items.value.findIndex((s) => s.id === updated.id)
  if (idx !== -1) {
    items.value[idx] = { ...items.value[idx], ...updated }
  }
}

async function cleanupDead() {
  if (!confirm('将删除所有路径失效的软件记录，确定?')) return
  try {
    const { data } = await cleanupDeadSoftware()
    alert(`已清理 ${data.removed_count} 条死链记录`)
    await loadList()
  } catch { /* ignore */ }
}

async function bulkGenerate() {
  const targets = itemsWithoutDescription.value
  if (targets.length === 0) return
  if (!confirm(`将为 ${targets.length} 个无描述的软件生成 AI 描述，确定?`)) return

  bulkGenerating.value = true
  bulkTotal.value = targets.length
  bulkProgress.value = 0

  let successCount = 0
  let failCount = 0

  for (const sw of targets) {
    try {
      const { data } = await generateSoftwareDescription(sw.id)
      if (data.success) {
        handleUpdated({ ...sw, description: data.description })
        successCount++
      } else {
        failCount++
      }
    } catch {
      failCount++
    }
    bulkProgress.value++
  }

  bulkGenerating.value = false
  alert(`批量生成完成：成功 ${successCount} 个，失败 ${failCount} 个`)
}

onMounted(loadList)
</script>
