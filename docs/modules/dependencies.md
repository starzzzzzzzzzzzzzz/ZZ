# 模块依赖关系

## 1. 核心模块结构
```
backend/
├── models/              # 模型定义
│   ├── mentor.py       # 导师模型
│   └── expert.py       # 专家模型
├── knowledge/          # 知识库管理
│   ├── vector_store.py # 向量存储
│   └── document.py     # 文档处理
├── data/              # 数据存储
├── config.py          # 配置文件
└── main.py            # 主程序入口
```

## 2. 模块依赖关系

### 2.1 导师模块（models/mentor.py）
- 依赖项：
  * LM Studio API
  * LangChain
  * 配置管理（config.py）
- 被依赖：
  * 主程序（main.py）
  * 知识检索服务

### 2.2 专家模块（models/expert.py）
- 依赖项：
  * ChromaDB
  * 文档处理模块（knowledge/document.py）
  * 向量存储（knowledge/vector_store.py）
- 被依赖：
  * 主程序（main.py）
  * 知识库管理服务

### 2.3 知识库模块（knowledge/）
- 依赖项：
  * ChromaDB
  * 文档处理库
  * 配置管理（config.py）
- 被依赖：
  * 专家模块
  * 文档管理服务

## 3. 接口定义

### 3.1 导师模型接口
```python
class MentorModel:
    async def process_query(self, query: str) -> str
    async def generate_search_query(self, query: str) -> str
    async def generate_answer(self, query: str, context: list) -> str
```

### 3.2 专家模型接口
```python
class ExpertModel:
    async def search_knowledge(self, query: str) -> list
    async def add_document(self, document: Document) -> bool
    async def update_knowledge(self, content: str) -> bool
```

### 3.3 知识库接口
```python
class VectorStore:
    async def store_document(self, document: Document) -> bool
    async def search_similar(self, query: str, limit: int) -> list
    async def update_vectors(self, content: str) -> bool
```

## 4. 数据流转关系

1. 文档处理流程
   - 文档上传 -> 文档处理 -> 向量化 -> 存储
   
2. 查询处理流程
   - 用户查询 -> 导师处理 -> 专家检索 -> 导师总结 -> 返回

## 5. 注意事项

1. 模块解耦
   - 通过接口通信
   - 避免直接依赖实现
   - 使用依赖注入

2. 版本控制
   - 接口变更需要同步更新
   - 保持向后兼容
   - 记录重要变更

3. 性能考虑
   - 异步操作
   - 缓存机制
   - 批量处理 