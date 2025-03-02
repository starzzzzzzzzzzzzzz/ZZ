# 系统架构设计

## 1. 整体架构

### 1.1 核心组件
- 前端界面 (Frontend)
- 后端服务 (Backend)
- 数据存储层 (Storage Layer)
  - PostgreSQL: 结构化数据存储
  - ChromaDB: 向量数据存储

### 1.2 技术栈
- 前端: Vue.js + TypeScript
- 后端: FastAPI + Python
- 数据库: 
  - PostgreSQL (文档元数据和分块管理)
  - ChromaDB (向量存储和相似度检索)
- ORM: SQLAlchemy
- 迁移工具: Alembic
- 向量模型: SentenceTransformer

## 2. 数据流

### 2.1 文档处理流程
1. 文档上传
2. 文档分块
3. 向量化处理
4. 数据持久化
   - 文档元数据 → PostgreSQL
   - 文本分块 → PostgreSQL
   - 向量数据 → ChromaDB

### 2.2 检索流程
1. 用户输入查询
2. 查询向量化
3. 向量相似度检索
4. 结果聚合和排序
5. 返回匹配文档

## 3. 存储设计

### 3.1 PostgreSQL 数据模型
- Documents 表
  - id: 文档唯一标识
  - kb_id: 知识库ID
  - title: 文档标题
  - meta_info: 元数据(JSON)
  - created_at: 创建时间
  - updated_at: 更新时间

- Chunks 表
  - id: 分块唯一标识
  - doc_id: 所属文档ID
  - content: 分块内容
  - chunk_index: 分块序号
  - vector_id: 对应的向量ID

### 3.2 ChromaDB 存储
- 按知识库ID组织collection
- 存储文本向量和元数据
- 支持高效的相似度检索

## 4. 接口设计

### 4.1 文档管理接口
- 文档上传
- 文档更新
- 文档删除
- 文档检索

### 4.2 知识库管理接口
- 知识库创建
- 知识库配置
- 知识库删除

## 5. 安全设计

### 5.1 数据安全
- 数据库访问控制
- 文档加密存储
- 定期数据备份

### 5.2 接口安全
- API认证授权
- 请求限流
- 输入验证

## 6. 扩展性设计

### 6.1 水平扩展
- 数据库主从复制
- 读写分离
- 负载均衡

### 6.2 功能扩展
- 插件化架构
- 模块化设计
- 配置化管理 