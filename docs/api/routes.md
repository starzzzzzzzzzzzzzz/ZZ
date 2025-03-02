# API 接口文档

## 1. 文档管理接口

### 1.1 上传文档
```http
POST /api/documents
Content-Type: multipart/form-data

{
    "file": File,            # 文档文件
    "kb_id": string,         # 知识库ID
    "title": string,         # 文档标题（可选）
    "metadata": object,      # 文档元数据（可选）
    "chunk_size": integer    # 分块大小（可选，默认500）
}

Response 200:
{
    "id": string,            # 文档ID
    "kb_id": string,         # 知识库ID
    "title": string,         # 文档标题
    "metadata": object,      # 文档元数据
    "chunk_count": integer,  # 分块数量
    "created_at": datetime   # 创建时间
}
```

### 1.2 获取文档
```http
GET /api/documents/{document_id}

Response 200:
{
    "id": string,            # 文档ID
    "kb_id": string,         # 知识库ID
    "title": string,         # 文档标题
    "content": string,       # 文档内容
    "metadata": object,      # 文档元数据
    "chunk_count": integer,  # 分块数量
    "created_at": datetime,  # 创建时间
    "updated_at": datetime   # 更新时间
}
```

### 1.3 删除文档
```http
DELETE /api/documents/{document_id}

Response 200:
{
    "message": "Document deleted successfully"
}
```

### 1.4 搜索文档
```http
POST /api/documents/search
Content-Type: application/json

{
    "query": string,         # 搜索查询
    "kb_id": string,        # 知识库ID
    "limit": integer,       # 返回结果数量限制（可选）
    "filters": object,      # 过滤条件（可选）
    "return_chunks": boolean # 是否返回匹配的具体分块（可选）
}

Response 200:
{
    "documents": [
        {
            "id": string,           # 文档ID
            "kb_id": string,        # 知识库ID
            "title": string,        # 文档标题
            "content": string,      # 文档内容（如果return_chunks=false）
            "metadata": object,     # 文档元数据
            "similarity": float,    # 相似度得分
            "matched_chunks": [     # 匹配的分块（如果return_chunks=true）
                {
                    "id": string,   # 分块ID
                    "content": string, # 分块内容
                    "index": integer,  # 分块序号
                    "similarity": float # 分块相似度得分
                }
            ]
        }
    ]
}
```

### 1.5 获取文档分块
```http
GET /api/documents/{document_id}/chunks

Response 200:
{
    "chunks": [
        {
            "id": string,        # 分块ID
            "content": string,   # 分块内容
            "index": integer,    # 分块序号
            "vector_id": string  # 向量ID
        }
    ],
    "total": integer           # 总分块数
}
```

### 1.6 重新生成文档分块
```http
POST /api/documents/{document_id}/rechunk
Content-Type: application/json

{
    "chunk_size": integer     # 新的分块大小（可选）
}

Response 200:
{
    "message": "Document rechunked successfully",
    "chunk_count": integer    # 新的分块数量
}
```

## 2. 知识库管理接口

### 2.1 创建知识库
```http
POST /api/knowledge-bases
Content-Type: application/json

{
    "name": string,          # 知识库名称
    "description": string    # 知识库描述（可选）
}

Response 200:
{
    "id": string,            # 知识库ID
    "name": string,          # 知识库名称
    "description": string,   # 知识库描述
    "created_at": datetime   # 创建时间
}
```

### 2.2 获取知识库列表
```http
GET /api/knowledge-bases

Response 200:
{
    "knowledge_bases": [
        {
            "id": string,            # 知识库ID
            "name": string,          # 知识库名称
            "description": string,   # 知识库描述
            "document_count": int,   # 文档数量
            "chunk_count": int,      # 分块总数
            "created_at": datetime   # 创建时间
        }
    ]
}
```

### 2.3 删除知识库
```http
DELETE /api/knowledge-bases/{kb_id}

Response 200:
{
    "message": "Knowledge base deleted successfully"
}
```

## 3. 系统管理接口

### 3.1 系统状态
```http
GET /api/system/status

Response 200:
{
    "status": string,                # 系统状态
    "version": string,               # 系统版本
    "database_status": {             # 数据库状态
        "postgresql": string,        # PostgreSQL状态
        "chromadb": string          # ChromaDB状态
    },
    "connection_pool": {             # 连接池状态
        "total": integer,           # 总连接数
        "used": integer,            # 使用中的连接数
        "available": integer        # 可用连接数
    }
}
```

### 3.2 系统统计
```http
GET /api/system/stats

Response 200:
{
    "total_knowledge_bases": int,    # 知识库总数
    "total_documents": int,          # 文档总数
    "total_chunks": int,            # 分块总数
    "storage_usage": {              # 存储使用情况
        "postgresql": {             # PostgreSQL存储统计
            "documents_size": string,
            "chunks_size": string,
            "total_size": string
        },
        "chromadb": {              # ChromaDB存储统计
            "embeddings_size": string,
            "total_size": string
        }
    },
    "performance_metrics": {        # 性能指标
        "avg_vectorization_time": float,   # 平均向量化时间
        "avg_search_time": float,         # 平均搜索时间
        "db_connection_pool": {           # 数据库连接池状态
            "total": int,
            "used": int,
            "available": int
        }
    }
}
```

### 3.3 数据一致性检查
```http
POST /api/system/check-consistency

Response 200:
{
    "status": "success",
    "inconsistencies": [
        {
            "type": string,     # 不一致类型
            "details": object   # 详细信息
        }
    ]
}
```

### 3.4 存储优化
```http
POST /api/system/optimize-storage

Response 200:
{
    "status": "success",
    "optimized": {
        "postgresql": {
            "space_saved": string
        },
        "chromadb": {
            "space_saved": string
        }
    }
}
```

## 4. 批量操作接口

### 4.1 批量上传文档
```http
POST /api/documents/batch-upload
Content-Type: multipart/form-data

{
    "files": File[],         # 文档文件列表
    "kb_id": string,         # 知识库ID
    "metadata": object       # 公共元数据（可选）
}

Response 200:
{
    "success_count": integer,    # 成功上传数量
    "failed_count": integer,     # 失败数量
    "failed_files": [           # 失败文件列表
        {
            "filename": string,
            "error": string
        }
    ]
}
```

### 4.2 批量删除文档
```http
POST /api/documents/batch-delete
Content-Type: application/json

{
    "document_ids": string[]    # 要删除的文档ID列表
}

Response 200:
{
    "success_count": integer,   # 成功删除数量
    "failed_count": integer,    # 失败数量
    "failed_ids": [            # 失败的文档ID列表
        {
            "id": string,
            "error": string
        }
    ]
}
```

## 5. 异步任务管理

### 5.1 获取任务状态
```http
GET /api/tasks/{task_id}/status

Response 200:
{
    "task_id": string,         # 任务ID
    "status": string,          # 任务状态
    "progress": float,         # 进度（0-100）
    "result": object,          # 任务结果（如果完成）
    "error": string           # 错误信息（如果失败）
}
```

## 6. 注意事项
1. 所有请求需要在header中设置：
   ```
   Content-Type: application/json
   ```

2. 错误响应格式：
   ```json
   {
     "code": 错误码,
     "message": "错误信息",
     "data": null
   }
   ```

3. 分页参数说明：
   - page: 从1开始的页码
   - page_size: 每页数量，默认10，最大100
