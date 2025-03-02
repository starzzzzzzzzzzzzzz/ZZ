# 数据库设计文档

## 1. PostgreSQL 数据库

### 1.1 Documents 表
文档主表，存储文档的基本信息和元数据。

```sql
CREATE TABLE documents (
    id VARCHAR PRIMARY KEY,           -- 文档唯一标识
    kb_id VARCHAR NOT NULL,           -- 知识库ID
    title VARCHAR,                    -- 文档标题
    meta_info JSONB,                  -- 元数据，使用JSONB类型存储灵活的元数据
    created_at TIMESTAMP,             -- 创建时间
    updated_at TIMESTAMP              -- 更新时间
);

-- 索引
CREATE INDEX idx_documents_kb_id ON documents(kb_id);
CREATE INDEX idx_documents_created_at ON documents(created_at);
```

### 1.2 Chunks 表
文档分块表，存储文档的分块内容。

```sql
CREATE TABLE chunks (
    id VARCHAR PRIMARY KEY,           -- 分块唯一标识
    doc_id VARCHAR REFERENCES documents(id), -- 关联的文档ID
    content TEXT,                     -- 分块内容
    chunk_index INTEGER,              -- 分块序号
    vector_id VARCHAR,                -- 对应的向量ID
    
    FOREIGN KEY (doc_id) REFERENCES documents(id)
);

-- 索引
CREATE INDEX idx_chunks_doc_id ON chunks(doc_id);
CREATE INDEX idx_chunks_vector_id ON chunks(vector_id);
```

## 2. ChromaDB 向量存储

### 2.1 Collection 组织
- 每个知识库对应一个Collection
- Collection名称格式：`{kb_id}`

### 2.2 向量数据结构
```python
{
    "ids": [vector_id],              # 向量ID
    "embeddings": [vector_data],     # 向量数据
    "metadatas": [{                  # 元数据
        "doc_id": str,               # 文档ID
        "chunk_id": str,             # 分块ID
        "chunk_index": int,          # 分块序号
        "total_chunks": int          # 总分块数
    }]
}
```

## 3. 数据库迁移

### 3.1 迁移工具
使用Alembic进行数据库版本控制和迁移管理

### 3.2 迁移文件位置
```
backend/
  ├── alembic/
  │   ├── versions/          # 迁移版本文件
  │   ├── env.py            # 迁移环境配置
  │   └── script.py.mako    # 迁移脚本模板
  └── alembic.ini           # Alembic配置文件
```

### 3.3 迁移命令
```bash
# 创建迁移
alembic revision --autogenerate -m "migration message"

# 应用迁移
alembic upgrade head

# 回滚迁移
alembic downgrade -1
```

## 4. 数据备份

### 4.1 PostgreSQL备份
```bash
# 完整备份
pg_dump -U username -d dbname > backup.sql

# 定期备份脚本
0 2 * * * pg_dump -U username -d dbname > /path/to/backup/backup_$(date +\%Y\%m\%d).sql
```

### 4.2 ChromaDB备份
- 定期备份持久化目录
- 向量数据的定期导出

## 5. 性能优化

### 5.1 PostgreSQL优化
- 适当的索引设计
- 查询优化
- 定期VACUUM
- 适当的配置调优

### 5.2 ChromaDB优化
- 批量处理
- 异步操作
- 合理的分块大小
- 向量维度选择
