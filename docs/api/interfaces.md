# API接口定义

## 1. 请求/响应数据结构
### 1.1 通用结构
```typescript
// 通用响应格式
interface ResponseModel<T> {
  code: number;      // 状态码
  message: string;   // 响应信息
  data?: T;         // 响应数据
}

// 分页请求参数
interface PaginationQuery {
  page_size: number;  // 每页数量
  page: number;       // 页码
}

// 分页响应格式
interface PaginationResponse<T> {
  total: number;      // 总数
  items: T[];        // 数据列表
}
```

### 1.2 知识库相关
```typescript
// 知识库创建请求
interface KnowledgeBaseCreate {
  name: string;           // 知识库名称
  description?: string;   // 知识库描述
  tags?: string[];       // 标签列表
}

// 知识库信息
interface KnowledgeBase {
  id: string;            // 知识库ID
  name: string;          // 知识库名称
  description?: string;  // 知识库描述
  tags?: string[];      // 标签列表
  doc_count: number;     // 文档数量
  created_at: string;    // 创建时间
  updated_at?: string;   // 更新时间
}

// 知识库更新请求
interface KnowledgeBaseUpdate {
  name?: string;         // 知识库名称
  description?: string;  // 知识库描述
  tags?: string[];      // 标签列表
}
```

### 1.3 文档相关
```typescript
// 文档上传请求
interface DocumentUpload {
  kb_id: string;         // 知识库ID
  title: string;         // 文档标题
  content: string;       // 文档内容
  metadata?: {           // 元数据
    source?: string;     // 来源
    author?: string;     // 作者
    tags?: string[];     // 标签
  };
}

// 文档信息
interface Document {
  id: string;           // 文档ID
  kb_id: string;        // 知识库ID
  title: string;        // 文档标题
  content: string;      // 文档内容
  chunk_count: number;  // 分块数量
  metadata: {           // 元数据
    source?: string;    // 来源
    author?: string;    // 作者
    tags?: string[];    // 标签
  };
  created_at: string;   // 创建时间
  updated_at?: string;  // 更新时间
}

// 文档查询参数
interface DocumentQuery {
  kb_id: string;        // 知识库ID
  page: number;         // 页码
  page_size: number;    // 每页数量
  keyword?: string;     // 搜索关键词
  tags?: string[];      // 标签过滤
}

// 文档更新请求
interface DocumentUpdate {
  title?: string;       // 文档标题
  content?: string;     // 文档内容
  metadata?: {          // 元数据
    source?: string;    // 来源
    author?: string;    // 作者
    tags?: string[];    // 标签
  };
}
```

### 1.4 对话相关
```typescript
// 对话查询请求
interface ChatQuery {
  kb_id: string;         // 知识库ID
  query: string;         // 用户问题
  history?: {            // 对话历史
    role: string;        // 角色：user/assistant
    content: string;     // 内容
  }[];
  search_params?: {      // 搜索参数
    top_k: number;       // 返回结果数量
    score_threshold: number; // 相似度阈值
  };
}

// 对话响应
interface ChatResponse {
  answer: string;        // 回答内容
  references: {          // 引用来源
    doc_id: string;      // 文档ID
    doc_title: string;   // 文档标题
    content: string;     // 相关内容片段
    score: number;       // 相关度分数
  }[];
  metadata: {            // 元数据
    tokens: number;      // token数量
    latency: number;     // 响应时间(ms)
  };
}

// 对话历史查询参数
interface ChatHistoryQuery {
  kb_id?: string;       // 知识库ID（可选）
  page: number;         // 页码
  page_size: number;    // 每页数量
  start_time?: string;  // 开始时间
  end_time?: string;    // 结束时间
}

// 对话记录
interface ChatHistory {
  id: string;           // 对话ID
  kb_id: string;        // 知识库ID
  query: string;        // 用户问题
  answer: string;       // 系统回答
  references: {         // 引用来源
    doc_id: string;     // 文档ID
    doc_title: string;  // 文档标题
    content: string;    // 相关内容片段
    score: number;      // 相关度分数
  }[];
  metadata: {           // 元数据
    tokens: number;     // token数量
    latency: number;    // 响应时间(ms)
  };
  created_at: string;   // 创建时间
}
```

## 2. 错误码定义
### 2.1 系统错误 (1000-1999)
- 1000: 系统内部错误
- 1001: 服务暂时不可用
- 1002: 请求超时
- 1003: LLM服务异常
- 1004: 向量服务异常

### 2.2 业务错误 (2000-2999)
- 2000: 知识库创建失败
- 2001: 知识库不存在
- 2002: 知识库名称已存在
- 2003: 知识库更新失败
- 2004: 知识库删除失败
- 2010: 文档上传失败
- 2011: 文档不存在
- 2012: 文档更新失败
- 2013: 文档删除失败
- 2014: 文档内容为空
- 2015: 文档格式不支持
- 2020: 对话生成失败
- 2021: 知识库检索失败
- 2022: 对话历史不存在
- 2023: 模型服务异常
- 2024: 对话内容不合规
- 2025: 超出最大对话长度

### 2.3 数据错误 (3000-3999)
- 3000: 参数验证失败
- 3001: 数据格式错误
- 3002: 数据不完整

## 3. 接口规范
### 3.1 认证方式
- 暂不需要认证

### 3.2 请求格式
- Content-Type: application/json
- 请求方法: GET, POST, PUT, DELETE
- 字符编码: UTF-8

### 3.3 响应格式
- Content-Type: application/json
- 字符编码: UTF-8
- 统一使用ResponseModel封装

### 3.4 版本控制
- 在URL中使用/api/v1/作为前缀
- 主版本号变更表示不兼容的API修改

## 4. 系统配置
### 4.1 向量模型配置
```typescript
interface VectorConfig {
  model: string;         // 向量模型名称，默认"shibing624/text2vec-base-chinese"
  device: string;        // 运行设备，可选"cpu"或"cuda"
  chunk_size: number;    // 文本分块大小，默认500
  chunk_overlap: number; // 分块重叠大小，默认50
}
```

### 4.2 LLM配置
```typescript
interface LLMConfig {
  api_base: string;      // LM Studio本地服务地址
  api_key?: string;      // API密钥（可选）
  temperature: number;   // 温度参数，控制随机性
  max_tokens: number;    // 最大生成长度
  top_p: number;        // 核采样阈值
}
```

### 4.3 存储配置
```typescript
interface StorageConfig {
  vector_store_path: string;  // 向量数据存储路径
  persist_directory: string;  // ChromaDB持久化目录
}
```
