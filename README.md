# 云杉数码 · 多功能智能售后客服

一个以虚构商家和演示数据构建的个人作品集项目。浏览器工作台连接 FastAPI，再由 LangGraph 调用本地 Ollama 模型、演示订单/商品/售后工具及 FAISS 知识库。

## 功能

- 中文自然语言咨询：订单、商品、售后政策、配送和公司资料
- 订单、商品、售后工具调用与最近一次运行轨迹展示
- 基于 7 份本地文档的 RAG 检索、文档清单与预览
- 当前进程内的多轮会话记忆；支持开始新会话
- 网页 API、Ollama 和模型安装状态面板

## 技术栈

Python、FastAPI、LangGraph、LangChain、Ollama、FAISS、原生 HTML/CSS/JavaScript。聊天模型为 `qwen2.5:3b`，向量模型为 `nomic-embed-text`。

## 本地运行

先安装并启动 Ollama，再下载模型：

```text
ollama pull qwen2.5:3b
ollama pull nomic-embed-text
```

安装 [requirements.txt](requirements.txt) 中的 Python 依赖后，在项目根目录启动：

```text
python -m uvicorn api:app --host 127.0.0.1 --port 8000
```

打开 `http://127.0.0.1:8000`。可用 `python rag.py` 单独验证知识库检索索引能否建立。修改知识库文档后，需重启 API 服务，才会在服务进程中重新建立索引。

## 服务器部署

参见 [DEPLOY.md](DEPLOY.md)。当前方案把 Ollama、FastAPI 与网页部署到同一台 Ubuntu 服务器，并用 Caddy 提供 HTTPS。公开部署前请确认服务器有足够内存和 CPU。

## 演示范围

云杉数码、订单、商品、价格、库存和政策均为虚构示例。项目未连接真实电商平台、物流或退款系统。会话只保存在服务进程内，服务重启后会清空；目前不适合存储真实客户信息。

本仓库不需要 OpenAI API 密钥。请勿将本地 `.env`、`venv`、真实客户资料或服务器密码提交到 GitHub。

