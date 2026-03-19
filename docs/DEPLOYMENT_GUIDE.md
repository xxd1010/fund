# 技术指标展示系统 - 部署文档

## 项目结构

```
.
├── backend/          # 后端服务
├── frontend/         # 前端应用
├── data/             # 数据文件
└── README.md         # 项目说明
```

## 技术栈

- **前端**: Vue 3 + Vite + ECharts + Element Plus
- **后端**: Python + FastAPI + Pandas + AkShare
- **部署**: Docker + Docker Compose

## 快速开始

### 方法一：使用Docker Compose（推荐）

1. **安装Docker和Docker Compose**
   - [Docker安装指南](https://docs.docker.com/get-docker/)
   - [Docker Compose安装指南](https://docs.docker.com/compose/install/)

2. **创建Docker Compose配置文件**

   ```yaml
   # docker-compose.yml
   version: "3.8"

   services:
     backend:
       build:
         context: ./backend
         dockerfile: Dockerfile
       ports:
         - "8000:8000"
       environment:
         - HOST=0.0.0.0
         - PORT=8000
       volumes:
         - ./data:/app/data
       restart: unless-stopped

     frontend:
       build:
         context: ./frontend
         dockerfile: Dockerfile
       ports:
         - "3000:80"
       depends_on:
         - backend
       restart: unless-stopped
   ```

3. **创建后端Dockerfile**

   ```dockerfile
   # backend/Dockerfile
   FROM python:3.9-slim

   WORKDIR /app

   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt

   COPY . .

   EXPOSE 8000

   CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
   ```

4. **创建前端Dockerfile**

   ```dockerfile
   # frontend/Dockerfile
   FROM node:16-alpine as build

   WORKDIR /app

   COPY package.json package-lock.json ./
   RUN npm install

   COPY . .
   RUN npm run build

   FROM nginx:alpine

   COPY --from=build /app/dist /usr/share/nginx/html

   COPY nginx.conf /etc/nginx/conf.d/default.conf

   EXPOSE 80

   CMD ["nginx", "-g", "daemon off;"]
   ```

5. **创建前端Nginx配置**

   ```nginx
   # frontend/nginx.conf
   server {
     listen 80;
     server_name localhost;

     location / {
       root /usr/share/nginx/html;
       index index.html;
       try_files $uri $uri/ /index.html;
     }

     location /api {
       proxy_pass http://backend:8000;
       proxy_set_header Host $host;
       proxy_set_header X-Real-IP $remote_addr;
       proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
       proxy_set_header X-Forwarded-Proto $scheme;
     }
   }
   ```

6. **启动服务**

   ```bash
   docker-compose up -d
   ```

7. **访问系统**
   - 前端应用: `http://localhost:3000`
   - 后端API文档: `http://localhost:8000/docs`

### 方法二：传统部署

#### 后端部署

1. **安装依赖**

   ```bash
   cd backend
   pip install -r requirements.txt
   ```

2. **启动服务**
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```

#### 前端部署

1. **安装依赖**

   ```bash
   cd frontend
   npm install
   ```

2. **构建生产版本**

   ```bash
   npm run build
   ```

3. **部署到Web服务器**
   - 将 `dist` 目录部署到 Nginx 或 Apache 服务器
   - 配置反向代理指向后端服务

## 配置说明

### 后端配置

- **.env文件**: 配置服务器端口、数据库连接等
- **requirements.txt**: 依赖包管理

### 前端配置

- **vite.config.js**: 开发服务器配置，包括代理设置
- **package.json**: 依赖包和脚本管理

## 环境变量

### 后端环境变量

- `HOST`: 服务器主机地址
- `PORT`: 服务器端口
- `DB_HOST`: 数据库主机
- `DB_PORT`: 数据库端口
- `DB_USER`: 数据库用户名
- `DB_PASSWORD`: 数据库密码
- `DB_NAME`: 数据库名称
- `REDIS_HOST`: Redis主机
- `REDIS_PORT`: Redis端口
- `REDIS_PASSWORD`: Redis密码
- `CACHE_TTL`: 缓存过期时间（秒）
- `LOG_LEVEL`: 日志级别

## 性能优化

### 后端优化

1. **数据缓存**: 使用Redis缓存计算结果
2. **异步处理**: 大计算任务使用异步处理
3. **数据库优化**: 合理索引和查询优化

### 前端优化

1. **代码分割**: 按需加载组件
2. **资源压缩**: 生产环境自动压缩
3. **缓存策略**: 合理的浏览器缓存策略

## 扩展性

### 添加新指标

1. 在 `technical_indicators.py` 中添加新的指标计算方法
2. 在 `backend/app/api/indicators.py` 中添加相应的API接口
3. 在前端 `Indicators.vue` 中添加指标选择选项

### 添加新数据源

1. 在 `backend/app/api/data.py` 中添加新的数据源处理逻辑
2. 在前端 `Data.vue` 中添加相应的数据源选项

### 添加新图表类型

1. 在 `backend/app/api/charts.py` 中添加新的图表类型支持
2. 在前端 `Charts.vue` 中添加相应的图表类型选项

## 监控和维护

### 日志管理

- 后端日志: `backend/ak_fund.log`
- 前端日志: 浏览器控制台

### 常见问题

1. **数据获取失败**
   - 检查网络连接
   - 检查API接口是否可用
   - 检查数据源配置

2. **图表渲染失败**
   - 检查数据格式是否正确
   - 检查图表配置是否合理
   - 检查浏览器兼容性

3. **性能问题**
   - 检查数据量是否过大
   - 检查缓存配置
   - 检查服务器资源

## 安全注意事项

1. **API安全**
   - 生产环境建议添加API密钥认证
   - 限制API访问频率
   - 验证输入数据

2. **数据安全**
   - 敏感数据加密存储
   - 定期备份数据
   - 限制数据访问权限

3. **服务器安全**
   - 定期更新系统和依赖
   - 配置防火墙规则
   - 监控异常访问

## 版本管理

### 版本控制

- 使用Git进行版本控制
- 遵循语义化版本规范

### 发布流程

1. 测试环境验证
2. 生产环境部署
3. 监控系统运行状态

## 技术支持

### 联系方式

- 技术支持: support@technical-indicators.com
- 文档地址: https://docs.technical-indicators.com

### 常见问题解答

**Q: 如何添加新的技术指标？**
A: 在 `technical_indicators.py` 中添加新的计算方法，然后在API和前端中添加相应的支持。

**Q: 如何优化系统性能？**
A: 启用Redis缓存，优化数据库查询，合理使用异步处理。

**Q: 如何部署到生产环境？**
A: 使用Docker Compose进行容器化部署，或部署到云服务器。

**Q: 如何处理大数据量？**
A: 实现数据分页，使用流式处理，优化计算算法。

---

**部署文档版本**: v1.0.0  
**更新日期**: 2026-03-15  
**维护者**: 技术指标展示系统团队
