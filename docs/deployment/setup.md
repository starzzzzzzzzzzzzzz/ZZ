# 部署设置指南

## 1. 环境要求
- Python 3.8+
- CUDA支持（可选，用于GPU加速）
- 足够的磁盘空间（建议20GB+）

## 2. 安装依赖
```bash
# 1. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
.\venv\Scripts\activate  # Windows

# 2. 安装依赖包
pip install -r requirements.txt
```

## 3. LM Studio设置
1. 下载安装LM Studio
   - 访问 https://lmstudio.ai/ 下载对应系统版本
   - 安装并启动应用

2. 下载模型
   - 在LM Studio中搜索并下载中文模型（推荐：Qwen-7B-Chat）
   - 等待下载完成

3. 启动本地服务
   - 在LM Studio中选择下载的模型
   - 点击"Start Server"启动服务
   - 默认地址：http://localhost:1234

## 4. 向量模型设置
1. 模型将在首次使用时自动下载
2. 默认保存位置：
   - Linux/Mac: ~/.cache/torch/sentence_transformers
   - Windows: C:\\Users\\USERNAME\\.cache\\torch\\sentence_transformers

## 5. ChromaDB设置
1. 创建数据目录：
```bash
mkdir -p data/vector_store
mkdir -p data/chromadb
```

2. 确保目录权限正确：
```bash
chmod 755 data/vector_store
chmod 755 data/chromadb
```

## 6. 环境配置
1. 复制环境变量模板：
```bash
cp .env.example .env
```

2. 编辑.env文件：
```env
# 应用配置
APP_NAME=知识库问答系统
API_V1_STR=/api/v1

# LM Studio配置
LLM_API_BASE=http://localhost:1234/v1
LLM_API_KEY=not-needed

# 向量模型配置
EMBEDDING_MODEL=shibing624/text2vec-base-chinese
EMBEDDING_DEVICE=cpu  # 或 cuda

# 存储配置
VECTOR_STORE_PATH=./data/vector_store
CHROMADB_PERSIST_DIR=./data/chromadb
```

## 7. 验证部署
1. 启动应用：
```bash
uvicorn app.main:app --reload
```

2. 检查服务状态：
```bash
curl http://localhost:8000/
```

应该看到类似响应：
```json
{
  "status": "ok",
  "message": "知识库问答系统服务正常运行"
}
```

## 8. 常见问题
1. LM Studio服务无法连接
   - 检查LM Studio是否正常启动
   - 确认端口1234是否被占用
   - 验证防火墙设置

2. 向量模型下载失败
   - 检查网络连接
   - 确认磁盘空间充足
   - 尝试手动下载并放置到缓存目录

3. ChromaDB权限问题
   - 检查目录权限
   - 确认用户有写入权限
   - 检查SELinux设置（如果适用） 