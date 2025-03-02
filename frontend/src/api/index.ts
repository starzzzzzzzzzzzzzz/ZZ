import request from './request'
import type { ApiResponse, PaginatedData } from './request'

export interface KnowledgeBase {
  id: number
  name: string
  description?: string
  created_at: string
  updated_at: string
}

export interface Document {
  id: number
  kb_id: number
  title: string
  content: string
  file_path: string
  file_size: number
  mime_type: string
  page_count: number
  vector_store_path: string
  chunk_count: number
  is_vectorized: boolean
  created_at: string
  updated_at: string
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  created_at?: string
}

export interface ChatResponse {
  answer: string
  references: Array<{
    doc_id: number
    title: string
    content: string
    score: number
  }>
}

// 知识库相关接口
export const knowledgeBaseApi = {
  list: async (): Promise<PaginatedData<KnowledgeBase>> => {
    return request.get<ApiResponse<PaginatedData<KnowledgeBase>>>('/api/v1/knowledge-bases')
  },
  
  async create(data: { name: string; description: string }): Promise<KnowledgeBase> {
    return request.post<ApiResponse<KnowledgeBase>>('/api/v1/knowledge-bases', data)
  },
  
  async delete(id: number): Promise<void> {
    await request.delete<ApiResponse<void>>(`/api/v1/knowledge-bases/${id}`)
  }
}

// 文档相关接口
export const documentApi = {
  async list(kbId: number): Promise<PaginatedData<Document>> {
    return request.get<ApiResponse<PaginatedData<Document>>>(`/api/v1/documents?kb_id=${kbId}`)
  },
  
  async upload(kbId: number, file: File): Promise<Document> {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('kb_id', kbId.toString())
    formData.append('title', file.name)
    return request.post<ApiResponse<Document>>('/api/v1/documents/pdf/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
  },
  
  async delete(kbId: number, docId: number): Promise<void> {
    await request.delete<ApiResponse<void>>(`/api/v1/documents/${docId}`)
  }
}

// 聊天相关接口
export const chatApi = {
  async sendMessage(kbId: number, message: string): Promise<ChatResponse> {
    return request.post<ApiResponse<ChatResponse>>(`/api/v1/chats/simple`, {
      content: message,
      kb_id: kbId
    })
  }
} 