import axios, { AxiosInstance, AxiosResponse, AxiosError } from 'axios'

export interface ApiResponse<T = any> {
  code: number
  message: string
  data: T
}

export interface PaginatedData<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  has_more: boolean
}

// 扩展 AxiosInstance 类型
interface CustomAxiosInstance extends Omit<AxiosInstance, 'get' | 'post' | 'put' | 'delete'> {
  get<T = any>(url: string, config?: any): Promise<T>
  post<T = any>(url: string, data?: any, config?: any): Promise<T>
  put<T = any>(url: string, data?: any, config?: any): Promise<T>
  delete<T = any>(url: string, config?: any): Promise<T>
}

const request: CustomAxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  timeout: 240000, // 240秒
  headers: {
    'Content-Type': 'application/json'
  }
}) as CustomAxiosInstance

// 请求拦截器
request.interceptors.request.use(
  (config) => {
    // 这里可以添加认证信息等
    return config
  },
  (error: AxiosError) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
request.interceptors.response.use(
  <T>(response: AxiosResponse<ApiResponse<T>>): T => {
    console.log('API响应原始数据:', response)
    const { data } = response
    console.log('API响应处理后数据:', data)
    if (data.code !== 200) {
      throw new Error(data.message || '请求失败')
    }
    return data.data
  },
  (error: AxiosError) => {
    let message = '请求失败'
    if (error.response) {
      const data = error.response.data as any
      message = data.message || `请求失败: ${error.response.status}`
    } else if (error.request) {
      if (error.code === 'ECONNABORTED') {
        message = '请求超时，模型正在思考中，请稍后重试'
      } else {
        message = '网络请求失败，请检查网络连接'
      }
    } else {
      message = error.message || '请求配置错误'
    }
    throw new Error(message)
  }
)

export default request 