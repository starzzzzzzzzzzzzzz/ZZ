# 智能知识库系统

基于大语言模型的智能知识库系统，支持文档管理和智能问答。系统采用前后端分离架构，提供高效的知识检索和对话式交互体验。

## 功能特点

- 知识库管理
  - 创建、删除和管理多个知识库
  - 知识库列表展示和切换
  - 知识库状态实时更新

- 文档管理
  - 支持 PDF、TXT、DOC、DOCX 格式文档上传
  - 文档自动向量化处理
  - 文档列表管理和删除功能
  - 文档状态显示（是否已向量化）
  - 文档大小和类型显示

- 智能对话
  - 基于知识库的智能问答
  - 支持上下文相关的对话
  - 展示对话引用的相关文档来源
  - 实时对话界面，支持历史消息展示
  - 混合检索策略（向量 + 关键词）

## 技术栈

### 前端

- Vue 3 + TypeScript
- Ant Design Vue 组件库
- Axios 请求处理
- Vite 构建工具

### 后端

- FastAPI
- SQLAlchemy + PostgreSQL
- ChromaDB (向量数据库)
- Sentence Transformers (文本向量化)
- Scikit-learn (TF-IDF 检索)
- Jieba (中文分词)

## 快速开始

### 环境要求

- Python 3.8+
- Node.js 16+
- PostgreSQL 12+

### 后端设置

1. 安装依赖：
```bash
cd backend
pip install -r requirements.txt
```

2. 配置环境变量：
```bash
cp .env.example .env
# 编辑 .env 文件，设置必要的环境变量
```

3. 初始化数据库：
```bash
alembic upgrade head
```

4. 启动服务：
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 前端设置

1. 安装依赖：
```bash
cd frontend
npm install
```

2. 启动开发服务器：
```bash
npm run dev
```

## 项目结构

```
.
├── backend/             # 后端代码
│   ├── app/            # 应用代码
│   │   ├── api/        # API 路由
│   │   ├── core/       # 核心配置
│   │   ├── models/     # 数据模型
│   │   ├── schemas/    # 数据验证
│   │   ├── services/   # 业务逻辑
│   │   └── utils/      # 工具函数
│   ├── alembic/        # 数据库迁移
│   └── tests/          # 测试代码
├── frontend/           # 前端代码
│   ├── src/           # 源代码
│   │   ├── api/       # API 调用
│   │   ├── views/     # 页面组件
│   │   ├── stores/    # 状态管理
│   │   └── router/    # 路由配置
│   └── public/        # 静态资源
└── docs/              # 项目文档
```

## 已完成功能

- [x] 基础知识库管理
  - [x] 知识库的创建、删除
  - [x] 知识库列表展示
  - [x] 知识库实时状态更新

- [x] 文档处理系统
  - [x] PDF文档上传和解析
  - [x] 文档自动向量化
  - [x] 文档分块存储
  - [x] 文档状态管理

- [x] 智能问答系统
  - [x] 基于 LLM 的智能对话
  - [x] 混合检索（向量+关键词）
  - [x] 相关度排序
  - [x] 实时对话界面

- [x] 系统优化
  - [x] 文档处理异步化
  - [x] 检索性能优化
  - [x] 前端响应式设计
  - [x] 错误处理完善

## 开发计划

- [ ] 用户系统
  - [ ] 用户注册和登录
  - [ ] 权限管理
  - [ ] 个人空间

- [ ] 知识库增强
  - [ ] 知识库分享
  - [ ] 协作编辑
  - [ ] 版本控制

- [ ] 高级功能
  - [ ] 批量导入
  - [ ] 导出功能
  - [ ] 高级搜索
  - [ ] 数据分析

## 贡献指南

欢迎提交 Issue 和 Pull Request。在提交 PR 之前，请确保：

1. 代码符合项目的编码规范
2. 添加了必要的测试
3. 更新了相关文档

## 许可证

MIT License 