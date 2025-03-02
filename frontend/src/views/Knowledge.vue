<template>
  <div class="knowledge-page">
    <a-row :gutter="16">
      <!-- 知识库列表 -->
      <a-col :span="8">
        <a-card title="知识库列表" :bordered="false">
          <template #extra>
            <a-button type="primary" @click="showCreateModal">
              新建知识库
            </a-button>
          </template>
          <a-list :loading="loading" :data-source="knowledgeBases">
            <template #renderItem="{ item }">
              <a-list-item>
                <a-list-item-meta
                  :title="item.name"
                  :description="item.description || '暂无描述'"
                />
                <template #actions>
                  <a-button type="link" @click="selectKnowledgeBase(item)">
                    查看文档
                  </a-button>
                  <a-popconfirm
                    title="确定要删除这个知识库吗？"
                    @confirm="deleteKnowledgeBase(item.id)"
                  >
                    <a-button type="link" danger>删除</a-button>
                  </a-popconfirm>
                </template>
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

      <!-- 文档列表 -->
      <a-col :span="16">
        <a-card
          :title="currentKnowledgeBase ? `${currentKnowledgeBase.name} - 文档列表` : '文档列表'"
          :bordered="false"
        >
          <template #extra v-if="currentKnowledgeBase">
            <a-upload
              :customRequest="handleUpload"
              :showUploadList="false"
              accept=".pdf,.txt,.doc,.docx"
              :beforeUpload="beforeUpload"
            >
              <a-button type="primary" :loading="uploading">上传文档</a-button>
            </a-upload>
          </template>
          <div v-if="!currentKnowledgeBase" class="empty-state">
            请选择一个知识库
          </div>
          <a-list v-else :loading="loading" :data-source="documents">
            <template #renderItem="{ item }">
              <a-list-item>
                <a-list-item-meta
                  :title="item.title"
                  :description="`${item.mime_type} - ${formatFileSize(item.file_size)}`"
                />
                <template #actions>
                  <a-tag :color="item.is_vectorized ? 'success' : 'warning'">
                    {{ item.is_vectorized ? '已向量化' : '未向量化' }}
                  </a-tag>
                  <a-popconfirm
                    title="确定要删除这个文档吗？"
                    @confirm="deleteDocument(item.id)"
                  >
                    <a-button type="link" danger>删除</a-button>
                  </a-popconfirm>
                </template>
              </a-list-item>
            </template>
            <template #empty>
              <div style="text-align: center; color: #999;">
                暂无文档
              </div>
            </template>
          </a-list>
        </a-card>
      </a-col>
    </a-row>

    <!-- 创建知识库对话框 -->
    <a-modal
      v-model:visible="createModalVisible"
      title="新建知识库"
      @ok="createKnowledgeBase"
    >
      <a-form :model="createForm" layout="vertical">
        <a-form-item label="名称" name="name" :rules="[{ required: true, message: '请输入知识库名称' }]">
          <a-input v-model:value="createForm.name" placeholder="请输入知识库名称" />
        </a-form-item>
        <a-form-item label="描述" name="description">
          <a-textarea v-model:value="createForm.description" placeholder="请输入知识库描述" />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { useAppStore } from '../stores'
import { knowledgeBaseApi, documentApi } from '../api'
import type { KnowledgeBase, Document } from '../api'
import type { PaginatedData } from '../api/request'

const store = useAppStore()
const loading = ref(false)
const uploading = ref(false)
const knowledgeBases = ref<KnowledgeBase[]>([])
const documents = ref<Document[]>([])
const currentKnowledgeBase = ref<KnowledgeBase | null>(null)
const createModalVisible = ref(false)
const createForm = ref({
  name: '',
  description: ''
})

// 上传前检查
const beforeUpload = (file: File) => {
  const isValidType = file.type === 'application/pdf' || 
                     file.type === 'text/plain' ||
                     file.type === 'application/msword' ||
                     file.type === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
  if (!isValidType) {
    message.error('只支持上传 PDF、TXT、DOC、DOCX 文件！')
    return false
  }
  return true
}

// 加载知识库列表
const loadKnowledgeBases = async () => {
  try {
    loading.value = true
    const response = await knowledgeBaseApi.list()
    console.log('知识库列表数据:', response)
    if (!response || !Array.isArray(response.items)) {
      console.error('知识库列表数据格式错误:', response)
      message.error('知识库列表数据格式错误')
      knowledgeBases.value = []
      return
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

// 加载文档列表
const loadDocuments = async (kbId: number) => {
  try {
    loading.value = true
    const { data } = await documentApi.list(kbId)
    documents.value = data.data.items || []
  } catch (error: any) {
    message.error(error.message || '加载文档列表失败')
    documents.value = []
  } finally {
    loading.value = false
  }
}

// 选择知识库
const selectKnowledgeBase = (kb: KnowledgeBase) => {
  currentKnowledgeBase.value = kb
  store.setCurrentKnowledgeBase(kb.id)
  loadDocuments(kb.id)
}

// 创建知识库
const createKnowledgeBase = async () => {
  try {
    loading.value = true
    await knowledgeBaseApi.create(createForm.value)
    message.success('创建成功')
    createModalVisible.value = false
    createForm.value = { name: '', description: '' }
    await loadKnowledgeBases()
  } catch (error: any) {
    message.error(error.message || '创建知识库失败')
  } finally {
    loading.value = false
  }
}

// 删除知识库
const deleteKnowledgeBase = async (id: number) => {
  try {
    loading.value = true
    await knowledgeBaseApi.delete(id)
    message.success('删除成功')
    if (currentKnowledgeBase.value?.id === id) {
      currentKnowledgeBase.value = null
      store.setCurrentKnowledgeBase(null)
      documents.value = []
    }
    await loadKnowledgeBases()
  } catch (error: any) {
    message.error(error.message || '删除知识库失败')
  } finally {
    loading.value = false
  }
}

// 上传文档
const handleUpload = async ({ file, onSuccess, onError }: { file: File; onSuccess: Function; onError: Function }) => {
  if (!currentKnowledgeBase.value) return
  
  try {
    uploading.value = true
    const response = await documentApi.upload(currentKnowledgeBase.value.id, file)
    if (response.data) {
      onSuccess(response.data)
      message.success('上传成功')
      // 延迟一下再刷新列表，等待后端处理完成
      setTimeout(() => {
        loadDocuments(currentKnowledgeBase.value!.id)
      }, 1000)
    } else {
      throw new Error('上传失败')
    }
  } catch (error: any) {
    onError(error)
    message.error(error.message || '上传文档失败')
  } finally {
    uploading.value = false
  }
}

// 删除文档
const deleteDocument = async (docId: number) => {
  if (!currentKnowledgeBase.value) return
  
  try {
    loading.value = true
    await documentApi.delete(currentKnowledgeBase.value.id, docId)
    message.success('删除成功')
    await loadDocuments(currentKnowledgeBase.value.id)
  } catch (error: any) {
    message.error(error.message || '删除文档失败')
  } finally {
    loading.value = false
  }
}

// 格式化文件大小
const formatFileSize = (bytes: number) => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return `${(bytes / Math.pow(k, i)).toFixed(2)} ${sizes[i]}`
}

// 显示创建对话框
const showCreateModal = () => {
  createModalVisible.value = true
}

onMounted(() => {
  loadKnowledgeBases()
})
</script>

<style scoped>
.knowledge-page {
  padding: 24px;
}

.empty-state {
  text-align: center;
  color: #999;
  padding: 32px;
}
</style> 