# Cognito · 知识主播内容摄入与检索平台

一个面向科普/知识类创作者的端到端知识库构建平台：从视频/音频链接或本地上传开始，完成“摄入 → 转写/回退 → 文本清洗与分块 → 嵌入与 FAISS 索引 → RAG 检索”，并提供基础的前端演示界面与鉴权能力。

## 目录
- [项目介绍](#项目介绍)
- [使用指南](#使用指南)
  - [环境准备](#环境准备)
  - [后端启动](#后端启动)
  - [任务队列启动](#任务队列启动)
  - [前端启动](#前端启动)
  - [API 文档与示例](#api-文档与示例)
  - [常见问题与故障排除](#常见问题与故障排除)
- [未来规划](#未来规划)
- [贡献指南](#贡献指南)
- [许可证](#许可证)
- [联系与支持](#联系与支持)
- [相关资源](#相关资源)

---

## 项目介绍

- 核心功能与价值定位
  - 支持以平台链接（B站/YouTube/TikTok 等）或本地音频文件为输入源，自动化构建面向检索的知识库。
  - 在网络/算力受限环境下提供“弹幕 XML → 文本”与 ASR 占位回退，确保端到端流程可用性。
  - 通过 FastEmbed + FAISS 实现多语种向量检索，并在索引缺失时自动回退到 LIKE 检索，保证查询不中断。
  - 适合作为创作者“内容资产化”的基础设施，将碎片化内容结构化为可检索的知识块。

- 适用用户与场景
  - 科普/知识类创作者、教育机构课程团队、播客/直播剪辑团队。
  - 搭建节目回放的知识检索、生成 FAQ、专题整理、课程知识库等。

- 主要技术栈与依赖
  - 后端：FastAPI、SQLAlchemy、MySQL、Redis、Celery、FAISS、fastembed、yt-dlp、Whisper（faster-whisper 与 openai-whisper 回退）
  - 前端：React + Vite
  - 运行环境：macOS（支持 Docker）、Python ≥ 3.11、Node.js ≥ 18

---

## 使用指南

### 环境准备

- 安装与版本建议
  - Python ≥ 3.11（建议使用 `venv`）
  - Node.js ≥ 18
  - Docker（用于启动 MySQL 与 Redis）

- 启动数据库与缓存（首次运行）
  ```bash
  docker-compose up -d
  ```

- 创建并填写环境变量文件 `.env`
  ```dotenv
  # 数据库
  DB_HOST=127.0.0.1
  DB_PORT=3306
  DB_USER=cognito
  DB_PASSWORD=cognito_pass
  DB_NAME=cognito

  # 后端服务
  BACKEND_HOST=0.0.0.0
  BACKEND_PORT=8000
  ALLOW_ORIGINS=http://localhost:5173

  # 任务队列与ASR
  REDIS_URL=redis://localhost:6379/0
  WHISPER_SKIP_FASTER=1             # 默认跳过 faster-whisper，优先走回退与轻量模型
  HF_HOME=./data/hf_cache           # 显式指定 HuggingFace 缓存目录
  ASR_QUEUE=cpu                     # ASR 任务队列（如启用 GPU 可改为 gpu）

  # 嵌入模型（可按需替换）
  EMBED_MODEL=sentence-transformers/paraphrase-multilingual-mpnet-base-v2
  ```

- 目录约定
  - `data/media`：视频音频及字幕/弹幕缓存
  - `data/index`：FAISS 索引与元数据
  - `data/hf_cache`：模型缓存目录

### 后端启动

```bash
# 创建虚拟环境并安装依赖
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

# 启动 FastAPI 服务（开发模式）
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 任务队列启动

```bash
# 启动 Celery worker（CPU 队列）
celery -A backend.app.celery_app.celery_app worker -Q cpu -l info

# 如需 GPU/高性能 ASR，可启动另一个 worker 监听 gpu 队列
# celery -A backend.app.celery_app.celery_app worker -Q gpu -l info
```

### 前端启动

```bash
cd frontend
npm install
npm run dev
```

默认前端运行在 `http://localhost:5173`，后端运行在 `http://localhost:8000`。

### API 文档与示例

- 鉴权：`/auth`
  - 注册：`POST /auth/register`
    - 请求体：`{ "username": string, "password": string, "role": "creator"|"admin"|"viewer" }`
    - 响应：`{ "message": "注册成功" }`
  - 登录：`POST /auth/login`
    - 请求体：`{ "username": string, "password": string }`
    - 响应：`{ "access_token": string, "token_type": "bearer" }`
  - 当前用户：`GET /auth/me`（需 `Authorization: Bearer <token>`）

- 上传：`/upload`
  - 音频上传：`POST /upload/audio`（`multipart/form-data`，字段 `file`，支持 `.mp3/.mp4/.wav/.m4a`）
    - 响应：`{ episode: { id, title, file_path, status }, message }`

- 节目：`/episodes`
  - 列表：`GET /episodes?page=1&size=10&status=processed`
    - 响应：`{ items: [{ id, title, status }...], page, size, total }`
  - 提交转录文本：`POST /episodes/transcript`（需鉴权）
    - 请求体：`{ episode_id: number, transcript: string }`
    - 响应：`{ task_id, message }`（使用 Celery 异步处理）
  - 任务状态：`GET /episodes/tasks/{task_id}`
    - 响应：`{ id, status, message, episode_id }`

- 摄入：`/intake`
  - 提交平台 URL：`POST /intake/submit_url`（需鉴权）
    - 请求体：`{ url: string }`（支持 `http/https`，前端会自动补全协议）
    - 响应：`{ task_id }`

- 任务：`/tasks`
  - 通用任务状态：`GET /tasks/{task_id}`
    - 响应：`{ id, status, message, episode_id }`

- 检索：`/query`
  - RAG 查询：`POST /query`
    - 请求体：`{ question: string, top_k?: number }`
    - 响应：`{ answer: string, chunks: [{ id, episode_id, text, start_time, end_time }] }`

- cURL 使用示例
  ```bash
  # 登录并获取令牌
  curl -sX POST http://localhost:8000/auth/login \
    -H 'Content-Type: application/json' \
    -d '{"username":"demo","password":"demo"}'

  # 上传音频文件
  curl -sX POST http://localhost:8000/upload/audio \
    -H "Authorization: Bearer <token>" \
    -F file=@/path/to/audio.m4a

  # 提交转录文本
  curl -sX POST http://localhost:8000/episodes/transcript \
    -H 'Content-Type: application/json' -H "Authorization: Bearer <token>" \
    -d '{"episode_id":1, "transcript":"...文本..."}'

  # 查询知识库
  curl -sX POST http://localhost:8000/query \
    -H 'Content-Type: application/json' \
    -d '{"question":"量子纠缠的定义是什么？","top_k":3}'
  ```

### 常见问题与故障排除

- 数据库连接失败
  - 检查 `docker-compose.yml` 是否已启动 MySQL（默认端口 `3306`）。
  - 确认 `.env` 中 `DB_HOST/DB_PORT/DB_USER/DB_PASSWORD/DB_NAME` 与数据库一致。

- CORS 报错
  - 修改 `.env` 中 `ALLOW_ORIGINS`，确保前端地址被允许。

- Celery 任务未执行
  - 确认 Redis 已启动；检查 `REDIS_URL`；确保启动了监听相应队列的 worker（如 `cpu`）。

- ASR 下载缓慢或失败
  - 设置 `WHISPER_SKIP_FASTER=1` 以跳过大型模型，优先弹幕/占位回退；必要时改用 `openai-whisper` 的较小模型。
  - 指定并创建 `HF_HOME` 缓存目录，避免权限或路径问题。

- 检索返回为空或索引未构建
  - 在构建索引前，查询接口会自动回退到 LIKE 检索；可通过提交转录文本或成功摄入带字幕的视频以触发索引构建。

- JWT 秘钥与安全
  - 当前示例秘钥为开发用途，请迁移到环境变量并在生产中替换强秘钥。

---

## 未来规划

- 短期（1–3 周）
  - 接入 Map-Reduce 摘要与高质量分块策略；完善时间戳映射。
  - 增加重排序与答案生成模块；丰富检索视图与元数据展示。
  - 前端加入任务监控与处理进度的更细粒度可视化。

- 中长期（1–3 月）
  - 支持多租户与角色权限；完善审计与配额。
  - 向量库可替换/扩展（如 Milvus / Weaviate）；加入在线重建与压缩策略。
  - 部署与运维：容器化、CI/CD、灰度发布、观测与报警；补齐集成测试。

---

## 贡献指南

- 提交流程
  - Fork 仓库并创建特性分支；完成修改后提 PR。
  - 在描述中清晰说明动机、方案与影响面。

- 代码规范
  - 前端遵循 ESLint 配置，尽量保持一致的 React Hooks 用法。
  - 后端遵循类型标注与模块化设计，严禁泄露密钥与凭证。

- 问题反馈
  - 使用 Issues 提交 Bug/建议，附复现步骤与环境信息。

---

## 许可证

本项目以 MIT 许可证发布。你可以自由地使用、复制、修改和分发本软件，但必须在分发时保留原始许可证声明与版权声明。详细条款请参阅：<https://opensource.org/licenses/MIT>

---

## 联系与支持

- 支持渠道：在仓库的 Issues 提交问题与需求；亦可在讨论区参与交流。
- 商务与合作：请通过邮箱 `your-email@example.com` 联系（请替换为实际地址）。

---

## 相关资源

- FastAPI: https://fastapi.tiangolo.com/
- SQLAlchemy: https://www.sqlalchemy.org/
- Celery: https://docs.celeryq.dev/
- FAISS: https://github.com/facebookresearch/faiss
- fastembed: https://github.com/qdrant/fastembed
- yt-dlp: https://github.com/yt-dlp/yt-dlp
- Whisper (faster-whisper): https://github.com/guillaumekln/faster-whisper
- React & Vite: https://react.dev/ / https://vitejs.dev/

---

如需更多使用示例或生产部署建议，请在 Issues 中提出，我们会持续完善文档与特性。