# 开发指南

## 1. 环境配置

### 1.1 系统要求
- Python 3.10+
- PostgreSQL 14+
- Node.js 16+

### 1.2 依赖安装
```bash
# 后端依赖
pip install -r requirements.txt

# 前端依赖
cd frontend && npm install
```

### 1.3 环境变量
```bash
# .env
DATABASE_URL=postgresql://user:password@localhost:5432/dbname
CHROMADB_PERSIST_DIR=/path/to/chromadb
SENTENCE_TRANSFORMER_MODEL=shibing624/text2vec-base-chinese
```

## 2. 项目结构

```
.
├── backend/                 # 后端代码
│   ├── alembic/            # 数据库迁移
│   ├── app/                # 应用代码
│   │   ├── core/          # 核心配置
│   │   ├── models/        # 数据模型
│   │   ├── services/      # 业务逻辑
│   │   └── utils/         # 工具函数
│   └── tests/             # 测试代码
├── frontend/              # 前端代码
├── docs/                  # 文档
└── docker/               # Docker配置
```

## 3. 开发流程

### 3.1 代码规范
- 遵循PEP 8规范
- 使用类型注解
- 编写文档字符串
- 使用black进行格式化

### 3.2 Git工作流
```bash
# 创建功能分支
git checkout -b feature/xxx

# 提交代码
git add .
git commit -m "feat: xxx"

# 合并主分支
git checkout main
git merge feature/xxx
```

### 3.3 数据库迁移
```bash
# 创建迁移
alembic revision --autogenerate -m "migration message"

# 应用迁移
alembic upgrade head

# 回滚迁移
alembic downgrade -1
```

## 4. 测试指南

### 4.1 单元测试
```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_xxx.py

# 生成覆盖率报告
pytest --cov=app tests/
```

### 4.2 集成测试
```bash
# 运行集成测试
pytest tests/integration/

# 使用特定配置
pytest tests/integration/ --env=test
```

## 5. 部署指南

### 5.1 使用Docker
```bash
# 构建镜像
docker-compose build

# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f
```

### 5.2 手动部署
```bash
# 后端服务
uvicorn app.main:app --host 0.0.0.0 --port 8000

# 前端服务
cd frontend && npm run build
```

## 6. 性能优化

### 6.1 数据库优化
- 使用适当的索引
- 优化查询语句
- 使用连接池
- 定期维护

### 6.2 向量存储优化
- 批量处理
- 异步操作
- 缓存策略
- 定期清理

## 7. 监控和日志

### 7.1 日志配置
```python
# logging配置
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'INFO',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': 'app.log',
            'level': 'ERROR',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
}
```

### 7.2 监控指标
- API响应时间
- 数据库性能
- 向量检索性能
- 系统资源使用

## 8. 安全建议

### 8.1 数据安全
- 使用环境变量存储敏感信息
- 实现数据加密
- 定期备份
- 访问控制

### 8.2 API安全
- 实现认证授权
- 输入验证
- 限流措施
- CORS配置 