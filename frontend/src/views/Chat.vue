<template>
  <div class="chat-page">
    <a-row :gutter="16">
      <!-- 知识库选择 -->
      <a-col :span="6">
        <a-card title="选择知识库" :bordered="false">
          <a-list :loading="loading" :data-source="knowledgeBases">
            <template #renderItem="{ item }">
              <a-list-item>
                <a-button
                  type="primary"
                  :class="{ active: currentKnowledgeBase?.id === item.id }"
                  @click="selectKnowledgeBase(item)"
                  style="width: 100%"
                >
                  {{ item.name }}
                </a-button>
              </a-list-item>
            </template>
            <template #empty>
              <div style="text-align: center; color: #999;">
                暂无知识库
              </div>
            </template>
          </a-list>
        </a-card>
      </a-col>

      <!-- 聊天区域 -->
      <a-col :span="18">
        <a-card
          :bordered="false"
          :title="currentKnowledgeBase ? `与 ${currentKnowledgeBase.name} 对话` : '请选择知识库'"
        >
          <!-- 消息列表 -->
          <div class="chat-messages" ref="messagesRef">
            <div v-if="!currentKnowledgeBase" class="empty-state">
              请先选择一个知识库开始对话
            </div>
            <template v-else>
              <div
                v-for="(message, index) in messages"
                :key="index"
                class="message"
                :class="message.role"
              >
                <div class="message-content">
                  {{ message.content }}
                </div>
                <div class="message-time" v-if="message.created_at">
                  {{ formatTime(message.created_at) }}
                </div>
              </div>
            </template>
          </div>

          <!-- 输入区域 -->
          <div class="chat-input">
            <a-input-search
              v-model:value="inputMessage"
              placeholder="输入消息..."
              enter-button="发送"
              :loading="sending"
              :disabled="!currentKnowledgeBase"
              @search="sendMessage"
            />
          </div>
        </a-card>
      </a-col>
    </a-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, nextTick } from 'vue'
import { message } from 'ant-design-vue'
import { useAppStore } from '../stores'
import { knowledgeBaseApi, chatApi } from '../api'
import type { KnowledgeBase, ChatMessage, ChatResponse } from '../api'
import type { PaginatedData } from '../api/request'

const store = useAppStore()
const loading = ref(false)
const sending = ref(false)
const knowledgeBases = ref<KnowledgeBase[]>([])
const currentKnowledgeBase = ref<KnowledgeBase | null>(null)
const messages = ref<ChatMessage[]>([])
const inputMessage = ref('')
const messagesRef = ref<HTMLElement | null>(null)

// 加载知识库列表
const loadKnowledgeBases = async () => {
  try {
    loading.value = true
    const response = await knowledgeBaseApi.list()
    console.log('知识库列表数据:', response)
    if (!response?.items) {
      throw new Error('返回数据为空')
    }
    knowledgeBases.value = response.items
  } catch (error: any) {
    console.error('加载知识库列表失败:', error)
    message.error(error.message || '加载知识库列表失败')
    knowledgeBases.value = []
  } finally {
    loading.value = false
  }
}

// 发送消息
const sendMessage = async () => {
  if (!currentKnowledgeBase.value || !inputMessage.value.trim()) return

  const userMessage: ChatMessage = {
    role: 'user',
    content: inputMessage.value,
    created_at: new Date().toISOString()
  }

  try {
    sending.value = true
    messages.value.push(userMessage)
    inputMessage.value = ''
    
    await nextTick()
    scrollToBottom()

    const response = await chatApi.sendMessage(
      currentKnowledgeBase.value.id,
      userMessage.content
    )
    console.log('聊天响应:', response)

    const assistantMessage: ChatMessage = {
      role: 'assistant',
      content: response.answer,
      created_at: new Date().toISOString()
    }
    messages.value.push(assistantMessage)
    await nextTick()
    scrollToBottom()
  } catch (error: any) {
    console.error('发送消息失败:', error)
    message.error(error.message || '发送消息失败')
  } finally {
    sending.value = false
  }
}

// 选择知识库
const selectKnowledgeBase = (kb: KnowledgeBase) => {
  currentKnowledgeBase.value = kb
  store.setCurrentKnowledgeBase(kb.id)
  messages.value = []
}

// 滚动到底部
const scrollToBottom = () => {
  if (messagesRef.value) {
    messagesRef.value.scrollTop = messagesRef.value.scrollHeight
  }
}

// 格式化时间
const formatTime = (isoString: string) => {
  const date = new Date(isoString)
  return date.toLocaleTimeString()
}

// 监听知识库变化
watch(() => store.currentKnowledgeBase, (newId) => {
  if (newId) {
    const kb = knowledgeBases.value.find(kb => kb.id === newId)
    if (kb) {
      currentKnowledgeBase.value = kb
    }
  } else {
    currentKnowledgeBase.value = null
  }
})

// 初始化
onMounted(async () => {
  await loadKnowledgeBases()
  const currentKbId = store.currentKnowledgeBase
  if (currentKbId) {
    const kb = knowledgeBases.value.find(kb => kb.id === currentKbId)
    if (kb) {
      selectKnowledgeBase(kb)
    }
  }
})
</script>

<style scoped>
.chat-page {
  padding: 24px;
  height: 100vh;
  display: flex;
  flex-direction: column;
}

.a-button.active {
  background-color: #1890ff;
  color: white;
}

.chat-messages {
  height: calc(100vh - 200px);
  overflow-y: auto;
  padding: 16px;
  background: #f5f5f5;
  border-radius: 4px;
  margin-bottom: 16px;
}

.message {
  margin-bottom: 16px;
  max-width: 80%;
}

.message.user {
  margin-left: auto;
}

.message.assistant {
  margin-right: auto;
}

.message-content {
  padding: 12px 16px;
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.message.user .message-content {
  background: #1890ff;
  color: #fff;
}

.message-time {
  font-size: 12px;
  color: #999;
  margin-top: 4px;
  text-align: right;
}

.chat-input {
  padding: 16px;
  background: #fff;
  border-top: 1px solid #f0f0f0;
}

.empty-state {
  text-align: center;
  color: #999;
  padding: 32px;
}
</style> 