<template>
  <!-- 弹窗遮罩 -->
  <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/40" @click.self="$emit('close')">
    <div class="bg-white rounded-xl shadow-xl w-full max-w-lg mx-4 p-6">
      <h3 class="text-lg font-bold text-gray-900 mb-4">映射目录到此处</h3>

      <div class="space-y-4">
        <!-- 目标位置（只读，链接将创建在这里） -->
        <div>
          <label class="block text-xs font-medium text-gray-500 mb-1">目标位置（链接创建在此）</label>
          <div
            class="flex items-center gap-2 px-3 py-2 text-sm bg-gray-50 border border-gray-200 rounded-lg font-mono text-gray-700"
            :title="targetDir"
          >
            <FolderOpen :size="16" class="text-yellow-500 flex-shrink-0" />
            <span class="truncate">{{ targetDir }}</span>
          </div>
        </div>

        <!-- 动画连接线 -->
        <div class="flex justify-center py-1">
          <div class="flex flex-col items-center gap-1">
            <ArrowUp :size="20" class="text-purple-400 animate-bounce" />
            <span class="text-[10px] text-purple-400 font-medium">JUNCTION</span>
          </div>
        </div>

        <!-- 源目录选择：从卡片中选择 或 手动输入 -->
        <div>
          <label class="block text-xs font-medium text-gray-500 mb-1">源目录（选择要映射的目录）</label>

          <!-- 模式切换 -->
          <div class="flex gap-1 mb-2">
            <button
              class="px-2.5 py-1 text-[11px] font-medium rounded-md transition-colors"
              :class="sourceMode === 'card'
                ? 'bg-purple-100 text-purple-700'
                : 'bg-gray-100 text-gray-500 hover:bg-gray-200'"
              @click="sourceMode = 'card'"
            >
              从卡片选择
            </button>
            <button
              class="px-2.5 py-1 text-[11px] font-medium rounded-md transition-colors"
              :class="sourceMode === 'manual'
                ? 'bg-purple-100 text-purple-700'
                : 'bg-gray-100 text-gray-500 hover:bg-gray-200'"
              @click="sourceMode = 'manual'"
            >
              手动输入
            </button>
          </div>

          <!-- 卡片选择模式 -->
          <div v-if="sourceMode === 'card'">
            <!-- 搜索框 -->
            <input
              v-model="cardSearch"
              type="text"
              placeholder="搜索软件或工作区名称..."
              class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent mb-2"
            />

            <!-- 卡片列表 -->
            <div class="max-h-48 overflow-y-auto border border-gray-200 rounded-lg divide-y divide-gray-50">
              <div v-if="loadingCards" class="py-4 text-center text-xs text-gray-400">加载中...</div>
              <div v-else-if="filteredCards.length === 0" class="py-4 text-center text-xs text-gray-400">
                {{ cardSearch ? '未找到匹配项' : '暂无可用目录' }}
              </div>
              <button
                v-for="card in filteredCards"
                :key="card.id"
                class="w-full flex items-center gap-2 px-3 py-2 text-left transition-colors"
                :class="selectedCard?.id === card.id
                  ? 'bg-purple-50 border-l-2 border-l-purple-500'
                  : 'hover:bg-gray-50'"
                @click="selectCard(card)"
              >
                <span class="text-sm flex-shrink-0">{{ card.type === 'software' ? '\uD83D\uDCE6' : '\uD83D\uDCC1' }}</span>
                <div class="min-w-0 flex-1">
                  <div class="text-xs font-medium text-gray-800 truncate">{{ card.name }}</div>
                  <div class="text-[10px] text-gray-400 font-mono truncate">{{ card.path }}</div>
                </div>
              </button>
            </div>
          </div>

          <!-- 手动输入模式 -->
          <div v-else class="flex items-center gap-2">
            <input
              v-model="manualSourcePath"
              type="text"
              placeholder="输入源目录路径"
              class="flex-1 px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent font-mono"
            />
            <button
              type="button"
              class="p-2 text-gray-400 hover:text-purple-500 transition-colors shrink-0"
              title="浏览..."
              @click="showBrowser = true"
            >
              <FolderOpen :size="16" />
            </button>
          </div>
        </div>

        <!-- 链接名称 -->
        <div>
          <label class="block text-xs font-medium text-gray-500 mb-1">链接名称</label>
          <input
            v-model="linkName"
            type="text"
            placeholder="留空则使用源目录名"
            class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent"
          />
        </div>

        <!-- 预览 -->
        <div v-if="fullLinkPath && resolvedSourcePath" class="bg-purple-50 rounded-lg px-3 py-2">
          <div class="text-[10px] text-purple-500 font-medium mb-1">将创建链接:</div>
          <div class="text-xs font-mono text-purple-700 truncate" :title="fullLinkPath">
            {{ fullLinkPath }}
          </div>
          <div class="text-[10px] text-purple-400 mt-0.5">
            &#8594; {{ resolvedSourcePath }}
          </div>
        </div>
      </div>

      <!-- 错误消息 -->
      <div v-if="error" class="mt-3 p-2 text-xs text-red-600 bg-red-50 rounded-lg">{{ error }}</div>

      <!-- 成功消息 -->
      <div v-if="successMsg" class="mt-3 p-2 text-xs text-green-600 bg-green-50 rounded-lg">{{ successMsg }}</div>

      <!-- 按钮 -->
      <div class="flex items-center justify-end gap-3 mt-5">
        <button
          class="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
          @click="$emit('close')"
        >
          {{ successMsg ? '关闭' : '取消' }}
        </button>
        <button
          v-if="!successMsg"
          class="px-4 py-2 text-sm font-medium text-white bg-purple-600 rounded-lg hover:bg-purple-700 disabled:opacity-50 transition-colors"
          :disabled="creating || !fullLinkPath || !resolvedSourcePath"
          @click="doCreate"
        >
          {{ creating ? '创建中...' : '创建链接' }}
        </button>
      </div>
    </div>
  </div>

  <!-- 文件夹浏览器 -->
  <FolderPickerDialog
    v-if="showBrowser"
    :initial-path="manualSourcePath"
    @confirm="onFolderPicked"
    @cancel="showBrowser = false"
  />
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { createSymlink, getSoftwareList, getWorkspaceList } from '@/api'
import FolderPickerDialog from '@/components/FolderPickerDialog.vue'
import { FolderOpen, ArrowUp } from 'lucide-vue-next'

interface CardOption {
  id: string
  name: string
  path: string
  type: 'software' | 'workspace'
}

const props = defineProps<{
  /** 目标目录：链接将创建在此目录下 */
  targetDir: string
}>()

const emit = defineEmits<{
  close: []
  created: []
}>()

// 源目录选择模式
const sourceMode = ref<'card' | 'manual'>('card')
const manualSourcePath = ref('')
const cardSearch = ref('')
const selectedCard = ref<CardOption | null>(null)
const allCards = ref<CardOption[]>([])
const loadingCards = ref(false)

// 其他状态
const linkName = ref('')
const creating = ref(false)
const error = ref('')
const successMsg = ref('')
const showBrowser = ref(false)

// 加载所有软件和工作区卡片
async function loadCards() {
  loadingCards.value = true
  try {
    const [swRes, wsRes] = await Promise.all([
      getSoftwareList(),
      getWorkspaceList(),
    ])
    const cards: CardOption[] = []
    for (const sw of swRes.data.items) {
      const dir = sw.install_dir || (sw.executable_path ? sw.executable_path.replace(/[\\/][^\\/]+$/, '') : '')
      if (dir) {
        cards.push({ id: sw.id, name: sw.name, path: dir, type: 'software' })
      }
    }
    for (const ws of wsRes.data.items) {
      if (ws.directory_path) {
        cards.push({ id: ws.id, name: ws.name, path: ws.directory_path, type: 'workspace' })
      }
    }
    allCards.value = cards
  } catch { /* ignore */ } finally {
    loadingCards.value = false
  }
}

onMounted(() => {
  loadCards()
})

// 搜索过滤
const filteredCards = computed(() => {
  if (!cardSearch.value.trim()) return allCards.value
  const q = cardSearch.value.toLowerCase()
  return allCards.value.filter(
    (c) => c.name.toLowerCase().includes(q) || c.path.toLowerCase().includes(q),
  )
})

function selectCard(card: CardOption) {
  selectedCard.value = selectedCard.value?.id === card.id ? null : card
}

// 解析出最终的源路径
const resolvedSourcePath = computed(() => {
  if (sourceMode.value === 'card') {
    return selectedCard.value?.path || ''
  }
  return manualSourcePath.value.trim()
})

// 从源路径中提取默认名称
const defaultName = computed(() => {
  const src = resolvedSourcePath.value
  if (!src) return ''
  const parts = src.replace(/[\\/]+$/, '').split(/[\\/]/)
  return parts[parts.length - 1] || ''
})

const fullLinkPath = computed(() => {
  if (!props.targetDir.trim()) return ''
  const name = linkName.value.trim() || defaultName.value
  if (!name) return ''
  const sep = props.targetDir.includes('/') ? '/' : '\\'
  return props.targetDir.replace(/[\\/]+$/, '') + sep + name
})

function onFolderPicked(path: string) {
  manualSourcePath.value = path
  showBrowser.value = false
}

async function doCreate() {
  if (!fullLinkPath.value || !resolvedSourcePath.value || creating.value) return

  creating.value = true
  error.value = ''
  successMsg.value = ''

  try {
    const { data } = await createSymlink(resolvedSourcePath.value, fullLinkPath.value)
    if (data.success) {
      successMsg.value = `链接已创建: ${data.link_path}`
      emit('created')
    } else {
      error.value = data.message || '创建失败'
    }
  } catch (e: unknown) {
    const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '创建链接失败'
    error.value = typeof detail === 'string' ? detail : JSON.stringify(detail)
  } finally {
    creating.value = false
  }
}
</script>
