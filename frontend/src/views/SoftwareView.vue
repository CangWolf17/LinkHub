<template>
  <div>
    <div class="flex items-center justify-between mb-6">
      <h2 class="text-xl font-bold text-gray-900">软件舱</h2>
      <div class="flex items-center gap-2">
        <!-- 排序选择 -->
        <select
          v-model="sortBy"
          class="px-2 py-1.5 text-xs border border-gray-200 rounded-lg bg-white text-gray-600 focus:outline-none focus:ring-1 focus:ring-blue-400"
        >
          <option value="updated_desc">最近更新</option>
          <option value="updated_asc">最早更新</option>
          <option value="name_asc">名称 A-Z</option>
          <option value="name_desc">名称 Z-A</option>
          <option value="created_desc">最近创建</option>
          <option value="created_asc">最早创建</option>
          <option value="used_desc">最近使用</option>
        </select>
        <!-- 标签筛选 -->
        <select
          v-if="allTags.length > 0"
          v-model="filterTag"
          class="px-2 py-1.5 text-xs border border-gray-200 rounded-lg bg-white text-gray-600 focus:outline-none focus:ring-1 focus:ring-blue-400"
        >
          <option value="">全部类型</option>
          <option v-for="tag in allTags" :key="tag" :value="tag">{{ tag }}</option>
        </select>
        <!-- 多选模式切换 -->
        <button
          class="px-3 py-1.5 text-xs font-medium rounded-lg transition-colors"
          :class="selectMode
            ? 'text-white bg-blue-600 hover:bg-blue-700'
            : 'text-blue-600 bg-blue-50 hover:bg-blue-100'"
          @click="toggleSelectMode"
        >
          {{ selectMode ? '取消选择' : '多选' }}
        </button>
        <!-- 多选模式下立即显示的批量操作按钮 -->
        <template v-if="selectMode">
          <!-- 全选 -->
          <button
            class="px-3 py-1.5 text-xs font-medium text-gray-600 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
            @click="toggleSelectAll"
          >
            {{ selectedIds.size === items.length ? '取消全选' : '全选' }}
          </button>
          <!-- 批量删除按钮 -->
          <button
            class="px-3 py-1.5 text-xs font-medium text-white bg-red-500 rounded-lg hover:bg-red-600 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            :disabled="selectedIds.size === 0"
            @click="batchDelete"
          >
            删除选中 ({{ selectedIds.size }})
          </button>
        </template>
        <button
          v-if="itemsWithoutDescription.length > 0 && !bulkGenerating"
          class="px-3 py-1.5 text-xs font-medium text-purple-600 bg-purple-50 rounded-lg hover:bg-purple-100 transition-colors disabled:opacity-50"
          @click="bulkGenerate"
        >
          AI 批量清洗 ({{ itemsWithoutDescription.length }})
        </button>
        <button
          v-if="bulkGenerating"
          class="px-3 py-1.5 text-xs font-medium text-red-600 bg-red-50 rounded-lg hover:bg-red-100 transition-colors"
          @click="stopBulkGenerate"
        >
          停止生成 ({{ bulkProgress }}/{{ bulkTotal }})
        </button>
        <button
          v-if="itemsWithoutTags.length > 0 && !bulkGenerating"
          class="px-3 py-1.5 text-xs font-medium text-indigo-600 bg-indigo-50 rounded-lg hover:bg-indigo-100 transition-colors"
          @click="bulkGenerateTags"
        >
          AI 批量标签 ({{ itemsWithoutTags.length }})
        </button>
        <button
          class="p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
          title="清理死链"
          @click="cleanupDead"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101" />
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.172 13.828a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.102 1.101" />
            <line x1="4" y1="4" x2="20" y2="20" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
          </svg>
        </button>
        <!-- 导入按钮 -->
        <button
          class="px-3 py-1.5 text-xs font-medium text-green-600 bg-green-50 rounded-lg hover:bg-green-100 transition-colors"
          @click="showImportModal = true"
        >
          + 导入
        </button>
      </div>
    </div>

    <!-- 导入弹窗 -->
    <div v-if="showImportModal" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40" @click.self="showImportModal = false">
      <div class="bg-white rounded-2xl shadow-xl w-full max-w-md p-6">
        <div class="flex items-center justify-between mb-4">
          <h3 class="text-base font-semibold text-gray-900">导入软件</h3>
          <button class="text-gray-400 hover:text-gray-600" @click="showImportModal = false">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <!-- 上传压缩包 -->
        <div
          class="mb-4 border-2 border-dashed rounded-xl p-6 text-center transition-all cursor-pointer"
          :class="isDragging ? 'border-blue-500 bg-blue-50' : 'border-gray-300 hover:border-gray-400'"
          @dragenter.prevent="isDragging = true"
          @dragover.prevent="isDragging = true"
          @dragleave.prevent="isDragging = false"
          @drop.prevent="onDrop"
          @click="triggerFileInput"
        >
          <div v-if="uploading" class="space-y-2">
            <div class="text-sm font-medium text-blue-600">{{ uploadStage }}</div>
            <div class="w-48 mx-auto h-1.5 bg-gray-200 rounded-full overflow-hidden">
              <div class="h-full bg-blue-500 rounded-full transition-all duration-300" :style="{ width: uploadProgress + '%' }" />
            </div>
            <div class="text-xs text-gray-500">{{ uploadMessage }}</div>
          </div>
          <div v-else>
            <div class="text-2xl mb-1">📦</div>
            <p class="text-sm text-gray-600">
              拖入压缩包或 <span class="text-blue-600 underline">点击选择</span>
            </p>
            <p class="text-[11px] text-gray-400 mt-1">支持 .zip / .7z / .tar.gz</p>
          </div>
        </div>

        <!-- 扫描目录导入 -->
        <button
          class="w-full py-2.5 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
          :disabled="scanning"
          @click="scanImport"
        >
          {{ scanning ? '扫描中...' : '从软件仓目录扫描导入' }}
        </button>
        <p v-if="scanResult" class="text-xs text-center mt-2" :class="scanResult.success ? 'text-green-600' : 'text-red-500'">
          {{ scanResult.message }}
        </p>
      </div>
    </div>

    <input ref="fileInput" type="file" accept=".zip,.7z,.tar,.tar.gz,.tar.bz2,.tar.xz,.tgz" class="hidden" @change="onFileSelect" />

    <!-- 最近使用 -->
    <div v-if="recentItems.length > 0 && !loading" class="mb-6">
      <h3 class="text-sm font-semibold text-gray-500 mb-3">最近使用</h3>
      <div class="flex gap-3 overflow-x-auto pb-2">
        <div
          v-for="sw in recentItems"
          :key="'recent-' + sw.id"
          class="flex-shrink-0 w-28 h-28 bg-white border border-gray-200 rounded-xl flex flex-col items-center justify-center gap-2 cursor-pointer hover:shadow-md hover:border-blue-300 transition-all group"
          :title="sw.name"
          @click="sw.executable_path ? handleLaunch(sw.executable_path) : undefined"
        >
          <span class="text-2xl">📦</span>
          <span class="text-[11px] font-medium text-gray-700 text-center px-2 truncate w-full group-hover:text-blue-600">{{ sw.name }}</span>
        </div>
      </div>
    </div>

    <!-- 软件卡片网格 -->
    <div v-if="loading" class="text-center py-12 text-gray-500 text-sm">加载中...</div>
    <div v-else-if="items.length === 0" class="text-center py-12 text-gray-400 text-sm">
      暂无软件记录，拖入压缩包开始安装
    </div>
    <template v-else>
      <!-- 正常软件 -->
      <div v-if="normalItems.length > 0" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <SoftwareCard
          v-for="sw in normalItems"
          :key="sw.id"
          :software="sw"
          :selectable="selectMode"
          :selected="selectedIds.has(sw.id)"
          @launch="handleLaunch"
          @delete="handleDelete"
          @updated="handleUpdated"
          @toggle-select="toggleSelect"
          @open-dir="handleOpenDir"
        />
      </div>
      <div v-else-if="missingItems.length > 0" class="text-center py-8 text-gray-400 text-sm">
        所有软件均路径失效
      </div>

      <!-- 路径失效折叠区域 -->
      <div v-if="missingItems.length > 0" class="mt-6">
        <button
          class="w-full flex items-center justify-center gap-2 py-2.5 px-4 bg-gray-100 hover:bg-gray-200 text-gray-500 rounded-lg transition-colors text-sm font-medium border border-gray-200"
          @click="showMissing = !showMissing"
        >
          <svg
            class="w-4 h-4 transition-transform duration-200"
            :class="showMissing ? 'rotate-180' : ''"
            fill="none" stroke="currentColor" viewBox="0 0 24 24"
          >
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
          </svg>
          路径失效 ({{ missingItems.length }})
        </button>
        <transition
          enter-active-class="transition-all duration-300 ease-out"
          enter-from-class="opacity-0 max-h-0"
          enter-to-class="opacity-100 max-h-[2000px]"
          leave-active-class="transition-all duration-200 ease-in"
          leave-from-class="opacity-100 max-h-[2000px]"
          leave-to-class="opacity-0 max-h-0"
        >
          <div v-if="showMissing" class="mt-4 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 overflow-hidden">
            <SoftwareCard
              v-for="sw in missingItems"
              :key="sw.id"
              :software="sw"
              :selectable="selectMode"
              :selected="selectedIds.has(sw.id)"
              @launch="handleLaunch"
              @delete="handleDelete"
              @updated="handleUpdated"
              @toggle-select="toggleSelect"
              @open-dir="handleOpenDir"
            />
          </div>
        </transition>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, nextTick, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getSoftwareList, uploadInstall, deleteSoftware, launchApp, openDir, cleanupDeadSoftware, generateSoftwareDescription, batchDeleteSoftware, scanAndImportSoftware, generateSoftwareTags, getLlmConfig } from '@/api'
import type { Software } from '@/api'
import SoftwareCard from '@/components/SoftwareCard.vue'

const route = useRoute()
const router = useRouter()

const items = ref<Software[]>([])
const loading = ref(true)
const isDragging = ref(false)
const uploading = ref(false)
const uploadStage = ref('')
const uploadProgress = ref(0)
const uploadMessage = ref('')
const fileInput = ref<HTMLInputElement | null>(null)

// 多选状态
const selectMode = ref(false)
const selectedIds = ref<Set<string>>(new Set())

// 路径失效折叠状态
const showMissing = ref(false)

// 导入弹窗状态
const showImportModal = ref(false)
const scanning = ref(false)
const scanResult = ref<{ success: boolean; message: string } | null>(null)

// 排序状态
const sortBy = ref('updated_desc')

// 标签筛选状态
const filterTag = ref('')

// 批量生成状态
const bulkGenerating = ref(false)
const bulkProgress = ref(0)
const bulkTotal = ref(0)
let bulkAbort = false
const softwareBlacklist = ref<string[]>([])

// 解析标签的工具函数
function parseTags(tagsStr: string | null): string[] {
  if (!tagsStr) return []
  try {
    const arr = JSON.parse(tagsStr)
    return Array.isArray(arr) ? arr : []
  } catch {
    return []
  }
}

// 所有可用标签（去重）
const allTags = computed(() => {
  const tagSet = new Set<string>()
  items.value.forEach((s) => {
    parseTags(s.tags).forEach((t) => tagSet.add(t))
  })
  return Array.from(tagSet).sort((a, b) => a.localeCompare(b, 'zh'))
})

// 按标签筛选
function filterByTag(list: Software[]): Software[] {
  if (!filterTag.value) return list
  return list.filter((s) => parseTags(s.tags).includes(filterTag.value))
}

function sortItems(list: Software[]): Software[] {
  const copy = [...list]
  switch (sortBy.value) {
    case 'name_asc':
      return copy.sort((a, b) => a.name.localeCompare(b.name, 'zh'))
    case 'name_desc':
      return copy.sort((a, b) => b.name.localeCompare(a.name, 'zh'))
    case 'created_desc':
      return copy.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    case 'created_asc':
      return copy.sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime())
    case 'updated_asc':
      return copy.sort((a, b) => new Date(a.updated_at).getTime() - new Date(b.updated_at).getTime())
    case 'used_desc':
      return copy.sort((a, b) => {
        const at = a.last_used_at ? new Date(a.last_used_at).getTime() : 0
        const bt = b.last_used_at ? new Date(b.last_used_at).getTime() : 0
        return bt - at
      })
    case 'updated_desc':
    default:
      return copy.sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime())
  }
}

const normalItems = computed(() => sortItems(filterByTag(items.value.filter((s) => !s.is_missing))))
const missingItems = computed(() => sortItems(filterByTag(items.value.filter((s) => s.is_missing))))

const recentItems = computed(() =>
  items.value
    .filter((s) => s.last_used_at && !s.is_missing)
    .sort((a, b) => new Date(b.last_used_at!).getTime() - new Date(a.last_used_at!).getTime())
    .slice(0, 8)
)

const itemsWithoutDescription = computed(() =>
  items.value.filter((s) => !s.description && !s.is_missing)
)

const itemsWithoutTags = computed(() =>
  items.value.filter((s) => !s.tags && !s.is_missing)
)

function toggleSelectMode() {
  selectMode.value = !selectMode.value
  if (!selectMode.value) {
    selectedIds.value = new Set()
  }
}

function toggleSelect(id: string) {
  const newSet = new Set(selectedIds.value)
  if (newSet.has(id)) {
    newSet.delete(id)
  } else {
    newSet.add(id)
  }
  selectedIds.value = newSet
}

function toggleSelectAll() {
  if (selectedIds.value.size === items.value.length) {
    selectedIds.value = new Set()
  } else {
    selectedIds.value = new Set(items.value.map((s) => s.id))
  }
}

async function batchDelete() {
  const count = selectedIds.value.size
  if (count === 0) return
  if (!confirm(`确定删除选中的 ${count} 条软件记录吗？（仅删除数据库记录，不删除本地文件）`)) return
  try {
    const ids = Array.from(selectedIds.value)
    const { data } = await batchDeleteSoftware(ids)
    alert(`已删除 ${data.deleted_count} 条记录`)
    selectedIds.value = new Set()
    selectMode.value = false
    await loadList()
  } catch {
    alert('批量删除失败，请重试')
  }
}

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
    showImportModal.value = false
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

async function scanImport() {
  scanning.value = true
  scanResult.value = null
  try {
    const { data } = await scanAndImportSoftware()
    scanResult.value = { success: true, message: data.message }
    if (data.imported > 0) {
      await loadList()
    }
  } catch {
    scanResult.value = { success: false, message: '扫描失败，请重试' }
  } finally {
    scanning.value = false
  }
}

async function handleLaunch(path: string) {
  try {
    await launchApp(path)
    // 刷新列表以更新最近使用时间
    await loadList()
  } catch (e: unknown) {
    const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '启动失败'
    alert(detail)
  }
}

async function handleOpenDir(path: string) {
  try {
    await openDir(path)
  } catch (e: unknown) {
    const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '打开失败'
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

function stopBulkGenerate() {
  bulkAbort = true
}

async function bulkGenerate() {
  // 加载黑名单
  try {
    const { data } = await getLlmConfig()
    softwareBlacklist.value = data.ai_blacklist_software || []
  } catch { /* ignore */ }
  const blackSet = new Set(softwareBlacklist.value.map(n => n.toLowerCase()))

  const targets = itemsWithoutDescription.value.filter(s => !blackSet.has(s.name.toLowerCase()))
  const skipped = itemsWithoutDescription.value.length - targets.length
  if (targets.length === 0) {
    alert(skipped > 0 ? `所有无描述软件均在黑名单中（${skipped} 个已跳过）` : '没有需要清洗的软件')
    return
  }
  const skipMsg = skipped > 0 ? `（${skipped} 个黑名单已跳过）` : ''
  if (!confirm(`将为 ${targets.length} 个无描述的软件执行 AI 清洗（生成描述）${skipMsg}，确定?`)) return

  bulkGenerating.value = true
  bulkTotal.value = targets.length
  bulkProgress.value = 0
  bulkAbort = false

  let successCount = 0
  let failCount = 0

  for (const sw of targets) {
    if (bulkAbort) break
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
  const stoppedMsg = bulkAbort ? '（已手动停止）' : ''
  alert(`批量清洗完成${stoppedMsg}：成功 ${successCount} 个，失败 ${failCount} 个`)
}

async function bulkGenerateTags() {
  // 加载黑名单
  try {
    const { data } = await getLlmConfig()
    softwareBlacklist.value = data.ai_blacklist_software || []
  } catch { /* ignore */ }
  const blackSet = new Set(softwareBlacklist.value.map(n => n.toLowerCase()))

  const targets = itemsWithoutTags.value.filter(s => !blackSet.has(s.name.toLowerCase()))
  const skipped = itemsWithoutTags.value.length - targets.length
  if (targets.length === 0) {
    alert(skipped > 0 ? `所有无标签软件均在黑名单中（${skipped} 个已跳过）` : '没有需要生成标签的软件')
    return
  }
  const skipMsg = skipped > 0 ? `（${skipped} 个黑名单已跳过）` : ''
  if (!confirm(`将为 ${targets.length} 个无标签的软件生成 AI 类型标签${skipMsg}，确定?`)) return

  bulkGenerating.value = true
  bulkTotal.value = targets.length
  bulkProgress.value = 0
  bulkAbort = false

  let successCount = 0
  let failCount = 0

  for (const sw of targets) {
    if (bulkAbort) break
    try {
      const { data } = await generateSoftwareTags(sw.id)
      if (data.success) {
        handleUpdated({ ...sw, tags: data.tags })
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
  const stoppedMsg = bulkAbort ? '（已手动停止）' : ''
  alert(`批量标签生成完成${stoppedMsg}：成功 ${successCount} 个，失败 ${failCount} 个`)
}

// 页面离开时自动停止批量生成
onBeforeUnmount(() => {
  bulkAbort = true
})

// 搜索高亮: 滚动到指定卡片并应用动画
function scrollToHighlight(id: string) {
  nextTick(() => {
    const el = document.querySelector(`[data-id="${id}"]`) as HTMLElement | null
    if (!el) return
    el.scrollIntoView({ behavior: 'smooth', block: 'center' })
    el.classList.add('search-highlight')
    setTimeout(() => el.classList.remove('search-highlight'), 2000)
    router.replace({ query: { ...route.query, highlight: undefined } })
  })
}

watch(() => route.query.highlight, (id) => {
  if (id && typeof id === 'string') {
    scrollToHighlight(id)
  }
})

onMounted(async () => {
  await loadList()
  if (route.query.highlight) {
    scrollToHighlight(route.query.highlight as string)
  }
})
</script>
