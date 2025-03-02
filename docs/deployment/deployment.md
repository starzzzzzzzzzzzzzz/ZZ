# 部署指南

## 1. 系统要求

### 1.1 硬件要求
- CPU: 4核+
- 内存: 8GB+
- 存储: 50GB+
- 网络: 100Mbps+

### 1.2 软件要求
- 操作系统: Ubuntu 20.04+ / CentOS 8+
- Python 3.10+
- PostgreSQL 14+
- Node.js 16+
- Docker 20.10+ (可选)
- Docker Compose 2.0+ (可选)

## 2. 环境准备

### 2.1 系统依赖
```bash
# Ubuntu
apt update
apt install -y python3-pip python3-venv postgresql postgresql-contrib

# CentOS
dnf update
dnf install -y python3-pip python3-virtualenv postgresql postgresql-server
```

### 2.2 Python环境
```bash
# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 2.3 数据库设置
```bash
# 创建数据库用户
sudo -u postgres createuser --interactive
# 创建数据库
sudo -u postgres createdb knowledge_base

# 配置数据库访问
sudo -u postgres psql
postgres=# ALTER USER your_user WITH PASSWORD 'your_password';
postgres=# GRANT ALL PRIVILEGES ON DATABASE knowledge_base TO your_user;
```

## 3. Docker部署

### 3.1 使用Docker Compose
```yaml
# docker-compose.yml
version: '3.8'

services:
  backend:
    build: 
      context: ./backend
      dockerfile: Dockerfile
    environment:
      - DATABASE_URL=postgresql://user:password@db:5432/knowledge_base
      - CHROMADB_PERSIST_DIR=/data/chromadb
    volumes:
      - chromadb_data:/data/chromadb
    depends_on:
      - db
    ports:
      - "8000:8000"

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "80:80"
    depends_on:
      - backend

  db:
    image: postgres:14
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=knowledge_base
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
  chromadb_data:
```

### 3.2 启动服务
```bash
# 构建并启动
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

## 4. 手动部署

### 4.1 后端部署
```bash
# 配置环境变量
export DATABASE_URL="postgresql://user:password@localhost:5432/knowledge_base"
export CHROMADB_PERSIST_DIR="/path/to/chromadb"
export SENTENCE_TRANSFORMER_MODEL="shibing624/text2vec-base-chinese"

# 应用数据库迁移
alembic upgrade head

# 启动服务
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 4.2 前端部署
```bash
# 安装依赖
cd frontend
npm install

# 构建
npm run build

# 使用nginx部署
server {
    listen 80;
    server_name your_domain.com;

    location / {
        root /path/to/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 5. 监控和维护

### 5.1 日志管理
```bash
# 配置日志轮转
/var/log/knowledge_base/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0640 www-data www-data
}
```

### 5.2 备份策略
```bash
# 数据库备份
pg_dump -U user knowledge_base > backup_$(date +%Y%m%d).sql

# ChromaDB备份
tar -czf chromadb_backup_$(date +%Y%m%d).tar.gz /path/to/chromadb
```

### 5.3 监控配置
```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'knowledge_base'
    static_configs:
      - targets: ['localhost:8000']
```

## 6. 安全配置

### 6.1 防火墙设置
```bash
# 开放必要端口
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 8000/tcp
```

### 6.2 SSL配置
```nginx
server {
    listen 443 ssl;
    server_name your_domain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    # SSL配置
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
}
```

### 6.3 安全检查清单
- [ ] 使用HTTPS
- [ ] 配置防火墙
- [ ] 更新系统包
- [ ] 设置数据库访问控制
- [ ] 配置日志监控
- [ ] 实现备份策略
- [ ] 设置资源限制 