# AI 爆款文章创作器 ✍️

<div align="center">

**AI 爆款文章创作器（Python 版）**

基于 FastAPI + Vue 3 的多智能体图文创作平台，自动完成从选题、大纲、正文到配图的全流程创作

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat-square&logo=fastapi&logoColor=white)
![Vue](https://img.shields.io/badge/Vue-3.5-4FC08D?style=flat-square&logo=vuedotjs&logoColor=white)
![Vite](https://img.shields.io/badge/Vite-7.0-646CFF?style=flat-square&logo=vite&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-blue?style=flat-square)

</div>

## 🏗 项目简介

AI 爆款文章创作器是一个基于 **多智能体协作** 的智能图文创作平台，通过 **5 个智能体协作** 完成从选题到图文文章的全自动创作，每个阶段都支持用户介入，实现人机协作的创作体验。

```
阶段1: 选题 → 生成 3-5 个标题方案 → 用户选择
阶段2: 标题 → 生成大纲 → 用户编辑 / AI 优化大纲
阶段3: 大纲 → 生成正文 → 分析配图需求 → 生成配图 → 图文合成
```

> 本项目为「编程导航」AI 爆款文章创作器实战课程的 Python 重写版：后端由 Spring Boot 重写为 FastAPI，功能与原版对齐，已移除 VIP 会员与支付体系，所有创作功能对所有用户开放。

## 🎯 核心价值

| 特性 | 说明 | 价值 |
|------|------|------|
| 🤖 多智能体协作 | 5 个 Agent 分工协作，统一编排 | 专业分工，质量更高 |
| 🎨 多元配图 | 6 种配图策略 + 自动降级 | 图文并茂，永不中断 |
| 📡 实时流式输出 | SSE 推送大纲/正文创作过程 | 所见即所得 |
| 🧑‍💻 人机协作 | 三阶段创作，每步可介入 | 创作可控 |
| ⚡ 异步高性能 | FastAPI 全异步栈 + Redis 缓存 | 响应迅速 |

## ✨ 功能特性

### 智能体协作

| 智能体 | 功能 | 说明 |
|--------|------|------|
| Agent 1 | 标题生成 | 根据选题生成 3-5 个标题方案供用户选择 |
| Agent 2 | 大纲生成 | 根据标题生成文章大纲（流式输出） |
| Agent 3 | 正文生成 | 根据大纲生成 Markdown 正文（流式输出） |
| Agent 4 | 配图分析 | 分析正文内容，生成配图需求 |
| Agent 5 | 配图生成 | 按策略并行获取图片并上传到 COS |
| 合成 | 合并图文 | 将配图按占位符插入正文生成完整图文 |

### 配图方式（策略模式）

系统采用策略模式实现多种配图方式，支持灵活扩展（所有用户可用）：

| 方式 | 说明 | 数据来源 |
|------|------|---------|
| Pexels | 高质量图库检索 | 关键词检索 |
| Mermaid | 流程图/架构图生成 | AI Prompt 生成 |
| Iconify | 图标库检索 | 关键词检索 |
| 表情包 | Bing 图片搜索 | 关键词检索 |
| Nano Banana | Gemini AI 生图 | AI Prompt 生成 |
| SVG Diagram | AI 概念示意图 | AI Prompt 生成 |
| Picsum | 随机图片 | 降级方案（自动触发） |

> 当配图方式失败时，系统会自动降级到 Picsum 随机图片，确保文章生成不中断。

### 文章风格

- 🔬 科技风格 - 专业严谨
- 💝 情感风格 - 温暖感人
- 📚 教育风格 - 通俗易懂
- 😄 轻松幽默 - 诙谐有趣

### SSE 实时通信

基于 Server-Sent Events 实现实时进度推送：

| 消息类型 | 说明 |
|---------|------|
| `AGENT1_COMPLETE` | 标题方案生成完成 |
| `AGENT2_STREAMING` | 大纲流式输出中 |
| `AGENT2_COMPLETE` | 大纲生成完成 |
| `AGENT3_STREAMING` | 正文流式输出中 |
| `AGENT3_COMPLETE` | 正文生成完成 |
| `AGENT4_COMPLETE` | 配图需求分析完成 |
| `IMAGE_COMPLETE` | 单张配图生成完成 |
| `AGENT5_COMPLETE` | 所有配图生成完成 |
| `MERGE_COMPLETE` | 图文合成完成 |
| `ERROR` | 错误通知 |

### 其他特性

- ✅ 文章管理（列表、详情、删除）
- ✅ Markdown 导出
- ✅ 智能体执行日志追踪与耗时统计
- ✅ 管理后台（用户管理、数据统计分析）

## 🛠 技术栈

### 后端

| 技术 | 版本 | 说明 |
|------|------|------|
| FastAPI | 0.115 | Web 框架 |
| Uvicorn | 0.32 | ASGI 服务器 |
| SQLAlchemy | 2.0 | ORM / 查询构建 |
| databases | 0.9 | 异步数据库访问 |
| PyMySQL | 1.1 | MySQL/MariaDB 驱动 |
| MariaDB / MySQL | 10.x / 8.0 | 数据存储 |
| Redis | 7.x | Session 与统计缓存 |
| OpenAI SDK | 1.58 | 调用 DashScope（通义千问）兼容接口 |
| Google Gen AI SDK | 1.35 | Gemini AI 生图（Nano Banana） |
| 腾讯云 COS SDK | 1.9 | 对象存储（配图上传） |

### 前端

| 技术 | 版本 | 说明 |
|------|------|------|
| Vue | 3.5 | 前端框架 |
| TypeScript | 5.8 | 类型安全 |
| Ant Design Vue | 4.2 | UI 组件库 |
| Vite | 7.0 | 构建工具 |
| Pinia | 3.0 | 状态管理 |
| Vue Router | 4.5 | 路由管理 |
| ECharts | 6.0 | 数据可视化 |
| Axios | 1.11 | HTTP 客户端 |
| marked | 17 | Markdown 渲染 |

## 🚀 快速开始

### 环境要求

- Python 3.10+（推荐使用 [uv](https://docs.astral.sh/uv/) 管理环境）
- Node.js 18+
- MariaDB 10.x（或 MySQL 8.0）
- Redis 7.x

### 1. 初始化数据库（Windows）

运行根目录的 [初始化数据库.bat](初始化数据库.bat)，脚本会：

1. 启动 MariaDB 容器（端口 3306，root 密码 `1234`，数据目录 `mariadb-data/`）
2. 启动 Redis 容器（端口 6379，密码 `1234`，数据目录 `redis-data/`）
3. 执行 `tools/main.exe`，将 [tools/init_database.sql](tools/init_database.sql) 应用到数据库（建库、建表、写入测试账号）

也可以手动执行 SQL：

```bash
mysql -uroot -p1234 < tools/init_database.sql
```

### 2. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env`，填写必需的 API Key：

```dotenv
DASHSCOPE_API_KEY=your-dashscope-api-key  # 必填，通义千问
PEXELS_API_KEY=your-pexels-api-key        # 必填，Pexels 图库
```

其余配置（COS、Gemini 生图、Mermaid 等）按需填写，见 [.env.example](.env.example) 中的注释。

### 3. 启动后端

```bash
uv sync                 # 安装依赖（首次）
uv run uvicorn app.main:app --reload
```

- 后端地址：http://localhost:8567
- 接口文档（Swagger UI）：http://localhost:8567/docs

### 4. 启动前端

```bash
cd frontend
npm install
npm run dev
```

前端页面：http://localhost:5173 （已配置代理，`/api` 请求转发到 `localhost:8567`）

## 🔧 环境变量说明

| 变量名 | 必需 | 默认值 | 说明 |
|--------|------|--------|------|
| DASHSCOPE_API_KEY | ✅ | dummy | 通义千问 API Key |
| PEXELS_API_KEY | ✅ | dummy | Pexels 图片 API Key |
| DASHSCOPE_MODEL | - | qwen-plus | 大模型名称 |
| DB_HOST / DB_PORT | - | 127.0.0.1 / 3306 | 数据库地址 |
| DB_NAME | - | ai_passage_creator | 数据库名 |
| DB_USER / DB_PASSWORD | - | root / 1234 | 数据库账号 |
| REDIS_HOST / REDIS_PORT | - | 127.0.0.1 / 6379 | Redis 地址 |
| REDIS_PASSWORD | - | 1234 | Redis 密码 |
| SERVER_PORT | - | 8567 | 后端端口 |
| TENCENT_COS_SECRET_ID / _SECRET_KEY | - | dummy | 腾讯云 COS（配图上传） |
| NANO_BANANA_API_KEY | - | dummy | Gemini AI 生图 |

完整列表见 [.env.example](.env.example)。

## 📁 项目结构

```
├── app/                               # FastAPI 后端
│   ├── main.py                        # 应用入口（路由注册、生命周期、异常处理）
│   ├── config.py                      # 配置管理（pydantic-settings，读取 .env）
│   ├── database.py / deps.py          # 数据库连接、登录态依赖
│   ├── agent/                         # 智能体模块
│   │   ├── agents/                    # 5 个智能体实现（标题/大纲/正文/配图分析/图文合成）
│   │   ├── orchestrator.py            # 三阶段编排器
│   │   ├── parallel/                  # 并行配图生成
│   │   └── context/                   # SSE 流式处理上下文
│   ├── constants/                     # 常量（Prompt、文章、用户）
│   ├── managers/                      # SseEmitterManager
│   ├── models/                        # SQLAlchemy 模型与枚举
│   ├── routers/                       # 路由（health/user/article/statistics）
│   ├── schemas/                       # Pydantic 请求/响应模型
│   ├── services/                      # 业务服务
│   │   ├── article_agent_service.py   # 智能体编排与 Prompt 构建
│   │   ├── article_service.py         # 文章状态流转
│   │   ├── article_async_service.py   # 异步阶段任务
│   │   ├── image_service_strategy.py  # 配图策略选择器
│   │   ├── pexels / mermaid / iconify / emoji_pack / nano_banana / svg_diagram_service.py
│   │   ├── cos_service.py             # COS 上传
│   │   ├── user_service.py / statistics_service.py
│   │   └── agent_log_service.py       # 智能体执行日志
│   └── utils/                         # 密码加密、Redis Session
├── frontend/                          # Vue 3 前端
│   ├── src/
│   │   ├── pages/                     # 页面（创作、文章、用户、管理后台）
│   │   ├── components/                # 公共组件
│   │   ├── api/                       # API 接口与 TS 类型
│   │   ├── stores/                    # Pinia 状态管理
│   │   └── utils/                     # SSE、权限、Markdown 工具
│   └── package.json
├── tools/
│   ├── init_database.sql              # 建库建表 + 测试数据
│   └── main.exe                       # 数据库初始化工具（执行上述 SQL）
├── 初始化数据库.bat                     # Windows 一键启动 MariaDB/Redis 并初始化
├── pyproject.toml / uv.lock           # Python 依赖（uv 管理）
└── .env.example                       # 环境变量模板
```

## 🗄 数据库设计

### 核心表

| 表名 | 说明 |
|------|------|
| user | 用户表（角色：user/admin） |
| article | 文章表（状态、阶段、配图方式、图文内容） |
| agent_log | 智能体执行日志（Prompt、输入输出、耗时） |

### 文章表关键字段

```sql
taskId               -- 任务ID（UUID）
phase                -- 当前阶段：PENDING/TITLE_GENERATING/TITLE_SELECTING/OUTLINE_GENERATING/OUTLINE_EDITING/CONTENT_GENERATING
style                -- 文章风格
titleOptions         -- 标题方案列表（JSON）
enabledImageMethods  -- 允许的配图方式（JSON 数组，空表示全部可用）
```

## 🔑 API Key 获取

| 服务 | 获取地址 | 说明 |
|------|---------|------|
| 通义千问 DashScope | https://bailian.console.aliyun.com | 必需，驱动所有文本智能体 |
| Pexels | https://www.pexels.com/api/ | 必需，默认图库检索 |
| 腾讯云 COS | https://console.cloud.tencent.com | 配图上传 |
| Gemini（Nano Banana） | Google AI Studio | AI 生图 |

## 🧪 测试账号

| 账号 | 密码 | 角色 |
|------|------|------|
| admin | 12345678 | 管理员 |
| user | 12345678 | 普通用户 |
| test | 12345678 | 测试账号 |

## 🏛 架构特点

### 多智能体编排

`ArticleAgentOrchestrator` 将 5 个智能体组织为三个阶段，阶段间通过用户确认衔接：

```python
async def execute_phase3(self, service, state, stream_handler):
    stream_context = StreamHandlerContext(stream_handler)
    await self.content_agent.run(service, state, stream_context.emit)   # 正文生成
    await self.image_analyzer_agent.run(service, state)                 # 配图需求分析
    await service.agent5_generate_images(state, stream_context.emit)    # 并行配图
    self.content_merger_agent.run(service, state)                       # 图文合成
```

### 配图策略模式

每种配图方式实现统一的 `ImageSearchService` 接口，由 `ImageServiceStrategy` 注册并调度：

```python
class ImageMethodEnum(str, Enum):
    PEXELS = "PEXELS"
    NANO_BANANA = "NANO_BANANA"
    MERMAID = "MERMAID"
    ICONIFY = "ICONIFY"
    EMOJI_PACK = "EMOJI_PACK"
    SVG_DIAGRAM = "SVG_DIAGRAM"
    PICSUM = "PICSUM"       # 降级方案
```

### 流式输出

基于 SSE（Server-Sent Events）实现实时进度推送：

- 大纲生成流式输出
- 正文创作流式输出
- 配图生成实时通知
- 阶段状态实时更新

## 🔧 扩展指南

### 添加新的配图方式

1. 在 `app/models/enums.py` 的 `ImageMethodEnum` 添加枚举值
2. 在 `app/services/` 下实现 `ImageSearchService` 接口：

```python
class NewMethodService(ImageSearchService):
    def get_method(self) -> ImageMethodEnum:
        return ImageMethodEnum.NEW_METHOD

    async def get_image_data(self, request: ImageRequest) -> Optional[ImageData]:
        ...
```

3. 在 `ImageServiceStrategy._register_services()` 中注册服务
4. （可选）在 `app/config.py` 添加配置项、在 `.env.example` 补充说明

### 添加新的文章风格

1. 在 `ArticleStyleEnum` 添加枚举值
2. 在 `app/constants/prompt.py` 添加对应的 Prompt 附加内容
3. 在 `ArticleAgentService._get_style_prompt()` 添加映射

## 👨‍💻 作者

<a href="https://codefather.cn">编程导航学习圈</a>
