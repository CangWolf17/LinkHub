import type { ComboOption } from '@/components/ApiUrlCombobox.vue'

export const LLM_API_PRESETS: ComboOption[] = [
  { label: 'OpenAI', value: 'https://api.openai.com/v1' },
  { label: 'Claude (Anthropic)', value: 'https://api.anthropic.com/v1' },
  { label: 'Gemini (Google)', value: 'https://generativelanguage.googleapis.com/v1beta/openai' },
  { label: 'DeepSeek', value: 'https://api.deepseek.com/v1' },
  { label: '智谱 (ZhiPu)', value: 'https://open.bigmodel.cn/api/paas/v4' },
  { label: 'Ollama (本地)', value: 'http://localhost:11434/v1' },
]
