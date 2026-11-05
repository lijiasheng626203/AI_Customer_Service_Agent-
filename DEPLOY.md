# 公开服务器部署（Ubuntu 24.04，单机 CPU 演示版）

这个项目把网页、FastAPI 和 Ollama 模型放在同一台云服务器上。访客打开公开链接时，你的电脑可以关机。模型本身没有按次 API 费用，但云服务器、域名和流量可能收费。

## 服务器准备

- 选择 Ubuntu 24.04、x86_64、至少 8 GB 内存、4 个 vCPU 和 40 GB 磁盘。8 GB 是低访问量演示的起点，不是性能保证；预算允许时优先 16 GB 内存。CPU 推理可能较慢。
- 记录服务器公网 IP、SSH 用户名和登录方式。服务器防火墙只开放 SSH、80、443；不要公开 8000 和 11434。
- 项目中只放虚构演示数据。不要上传本地 `.env`、`venv`、`__pycache__` 或真实客户资料。

## 1. 在 Windows 项目目录创建上传包

项目根目录是 `C:\Users\English\Desktop\AI_Customer_Service_Agent`。用 PowerShell 执行：

```powershell
$projectDir = "C:\Users\English\Desktop\AI_Customer_Service_Agent"
$releaseFiles = @(
  "$projectDir\api.py",
  "$projectDir\graph.py",
  "$projectDir\rag.py",
  "$projectDir\requirements.txt",
  "$projectDir\knowledge_base",
  "$projectDir\static",
  "$projectDir\tools",
  "$projectDir\deploy"
)
Compress-Archive -LiteralPath $releaseFiles -DestinationPath "$projectDir\customer-service-deploy.zip" -Force
```

只打包列表中的文件；检查压缩包中没有 `.env` 和 `venv`。上传时将 `SERVER_IP` 和 `SSH_USER` 换成你自己的信息：

```powershell
scp "$projectDir\customer-service-deploy.zip" SSH_USER@SERVER_IP:~/
```

## 2. 在服务器安装 Python 和 Ollama

先通过 SSH 登录服务器。以下命令都在服务器的 Linux 终端执行：

```bash
sudo apt update
sudo apt install -y python3-venv python3-pip unzip curl
curl -fsSL https://ollama.com/install.sh | sh
sudo systemctl enable --now ollama
ollama pull qwen2.5:3b
ollama pull nomic-embed-text
ollama list
```

先确认 `ollama list` 同时显示两个模型。

## 3. 安装项目

```bash
sudo useradd --system --home /opt/customer-service --shell /usr/sbin/nologin customerai
sudo mkdir -p /opt/customer-service
sudo unzip ~/customer-service-deploy.zip -d /opt/customer-service
sudo chown -R customerai:customerai /opt/customer-service
sudo -u customerai python3 -m venv /opt/customer-service/.venv
sudo -u customerai /opt/customer-service/.venv/bin/python -m pip install -r /opt/customer-service/requirements.txt
cd /opt/customer-service
sudo -u customerai /opt/customer-service/.venv/bin/python rag.py
```

`python rag.py` 是一次本地检索验证。网站启动时还会重建内存中的 FAISS 索引。

## 4. 让服务开机自动运行

```bash
sudo cp /opt/customer-service/deploy/customer-service.service /etc/systemd/system/customer-service.service
sudo systemctl daemon-reload
sudo systemctl enable --now customer-service
sudo systemctl status customer-service --no-pager
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/system/status
```

状态接口应显示 Ollama 在线、两个模型已安装、知识库有 7 份文档。若启动失败，运行 `sudo journalctl -u customer-service -n 100 --no-pager` 查看日志。

## 5. 配置公网网址和 HTTPS

先把域名的 A 记录指向服务器公网 IP，确认 80、443 端口可从公网访问。按 [Caddy 官方 Ubuntu 安装说明](https://caddyserver.com/docs/install)安装 Caddy，然后复制配置：

```bash
sudo cp /opt/customer-service/deploy/Caddyfile.example /etc/caddy/Caddyfile
sudo nano /etc/caddy/Caddyfile
```

把第一行 `support.example.com` 改为你自己的域名，保存后运行：

```bash
sudo caddy validate --config /etc/caddy/Caddyfile
sudo systemctl reload caddy
```

Caddy 会在域名解析和 80、443 端口正常时申请并续期 HTTPS 证书。用另一台电脑打开 `https://你的域名`，测试聊天、知识库预览和状态面板。

## 当前演示版的边界

- 会话信息仅保存在单个 Python 进程内；服务重启或服务器重启后会清空，因此服务配置固定为一个 worker。
- 订单、库存、公司和政策都是演示数据，没有连接真实业务系统。
- 这是低访问量作品集部署方案。正式服务需要用户身份验证、持久化会话、访问限流、日志和监控。
