import json
import os
import re
from datetime import datetime
from pathlib import Path
from threading import Lock
from urllib.request import urlopen

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from graph import graph


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

INDEX_FILE = BASE_DIR / "static" / "index.html"
KNOWLEDGE_BASE_DIR = BASE_DIR / "knowledge_base"

# 模型名称应与 graph.py、rag.py 中的配置一致。
CHAT_MODEL_NAME = os.getenv("OLLAMA_CHAT_MODEL", "qwen2.5:3b")
EMBEDDING_MODEL_NAME = os.getenv(
    "OLLAMA_EMBEDDING_MODEL",
    "nomic-embed-text",
)
OLLAMA_TAGS_URL = "http://127.0.0.1:11434/api/tags"

# 演示版会话记忆：存储在当前 Python 进程内，服务重启后会清空。
SESSIONS: dict[str, list[BaseMessage]] = {}
SESSION_ORDER_IDS: dict[str, str] = {}
SESSIONS_LOCK = Lock()

MAX_USER_TURNS = 10
MAX_SESSIONS = 100

# 匹配 5 位及以上数字作为演示订单号，不写死某一个订单号。
ORDER_ID_PATTERN = re.compile(r"(?<!\d)(\d{5,})(?!\d)")

ORDER_LOOKUP_WORDS = (
    "查", "查询", "状态", "到哪", "到哪里", "物流", "发货", "进度"
)
ORDER_REFERENCE_WORDS = (
    "它", "这个订单", "该订单", "那个订单", "订单呢"
)


app = FastAPI(
    title="多功能智能售后客服 API",
    description="连接网页工作台与本地 LangGraph Agent",
    version="1.4.0",
)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000, description="用户发送的问题")
    session_id: str = Field(..., min_length=1, max_length=100)


class TraceEvent(BaseModel):
    step: str
    detail: str


class ChatResponse(BaseModel):
    answer: str
    trace: list[TraceEvent]


@app.get("/", include_in_schema=False)
def home():
    if not INDEX_FILE.exists():
        raise HTTPException(
            status_code=404,
            detail="网页文件不存在，请确认 static/index.html 已创建。",
        )
    return FileResponse(INDEX_FILE)


@app.get("/health")
def health_check():
    """检查 FastAPI 网页 API 是否正常运行。"""
    return {
        "status": "ok",
        "service": "customer-service-agent",
    }


def get_knowledge_documents():
    """读取 knowledge_base 目录中实际存在的 .txt 文档。"""
    if not KNOWLEDGE_BASE_DIR.exists():
        return []

    documents = []

    for file_path in sorted(KNOWLEDGE_BASE_DIR.glob("*.txt")):
        if not file_path.is_file():
            continue

        file_stat = file_path.stat()

        documents.append({
            "name": file_path.name,
            "size_bytes": file_stat.st_size,
            "modified_time": datetime.fromtimestamp(
                file_stat.st_mtime
            ).isoformat(timespec="seconds"),
        })

    return documents


@app.get("/system/status")
def get_system_status():
    """实时检查 Ollama 服务和本地模型安装状态。"""
    ollama_online = False
    installed_models = []
    ollama_error = None

    try:
        with urlopen(OLLAMA_TAGS_URL, timeout=3) as response:
            ollama_data = json.loads(response.read().decode("utf-8"))

        installed_models = [
            model.get("name", "")
            for model in ollama_data.get("models", [])
            if model.get("name")
        ]
        ollama_online = True

    except Exception as exc:
        ollama_error = str(exc)

    def model_is_installed(model_name: str) -> bool:
        return any(
            installed_name == model_name
            or installed_name == f"{model_name}:latest"
            for installed_name in installed_models
        )

    documents = get_knowledge_documents()

    return {
        "api": "online",
        "ollama": "online" if ollama_online else "offline",
        "chat_model": CHAT_MODEL_NAME,
        "chat_model_installed": model_is_installed(CHAT_MODEL_NAME),
        "embedding_model": EMBEDDING_MODEL_NAME,
        "embedding_model_installed": model_is_installed(
            EMBEDDING_MODEL_NAME
        ),
        "installed_models": installed_models,
        "knowledge_document_count": len(documents),
        "ollama_error": ollama_error,
    }


@app.get("/knowledge-base")
def get_knowledge_base():
    """动态返回 knowledge_base 目录里的文档清单。"""
    documents = get_knowledge_documents()

    return {
        "count": len(documents),
        "documents": documents,
    }


@app.get("/knowledge-base/{filename}")
def preview_knowledge_document(filename: str):
    """预览知识库目录中的单个 TXT 文档。"""
    if Path(filename).name != filename or not filename.lower().endswith(".txt"):
        raise HTTPException(status_code=400, detail="只能预览知识库中的 TXT 文件。")

    file_path = KNOWLEDGE_BASE_DIR / filename
    if file_path.resolve().parent != KNOWLEDGE_BASE_DIR.resolve():
        raise HTTPException(status_code=400, detail="无效的文档路径。")
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="文档不存在。")

    try:
        with file_path.open("r", encoding="utf-8") as document_file:
            content = document_file.read(12001)
    except UnicodeError:
        raise HTTPException(status_code=422, detail="文档不是 UTF-8 编码。")

    return {
        "name": filename,
        "content": content[:12000],
        "truncated": len(content) > 12000,
    }


@app.delete("/sessions/{session_id}")
def delete_session(session_id: str):
    """清除一段会话的聊天记忆和当前订单号。"""
    with SESSIONS_LOCK:
        SESSIONS.pop(session_id, None)
        SESSION_ORDER_IDS.pop(session_id, None)

    return {"status": "cleared"}


def keep_recent_turns(messages: list[BaseMessage]) -> list[BaseMessage]:
    """保留最近 10 轮完整对话。"""
    human_indexes = [
        index
        for index, message in enumerate(messages)
        if getattr(message, "type", "") == "human"
    ]

    if len(human_indexes) <= MAX_USER_TURNS:
        return messages

    return messages[human_indexes[-MAX_USER_TURNS]:]


def save_session(session_id: str, messages: list[BaseMessage]) -> None:
    """限制演示服务在内存中保存的会话数量。"""
    with SESSIONS_LOCK:
        SESSIONS.pop(session_id, None)
        SESSIONS[session_id] = keep_recent_turns(messages)
        while len(SESSIONS) > MAX_SESSIONS:
            old_session_id = next(iter(SESSIONS))
            SESSIONS.pop(old_session_id, None)
            SESSION_ORDER_IDS.pop(old_session_id, None)


def was_asked_for_order_id(history: list[BaseMessage]) -> bool:
    """检查客服上一轮是否正在等待用户提供订单号。"""
    for message in reversed(history):
        if getattr(message, "type", "") == "ai":
            content = str(getattr(message, "content", ""))
            return (
                "订单号" in content
                and any(word in content for word in ("提供", "告诉", "发我"))
            )
    return False


def make_trace(messages: list[BaseMessage]) -> list[TraceEvent]:
    """从本轮新增的 LangGraph 消息生成工具调用轨迹。"""
    trace = []

    for message in messages:
        for tool_call in getattr(message, "tool_calls", []):
            tool_name = tool_call.get("name", "未知工具")
            tool_args = tool_call.get("args", {})
            trace.append(
                TraceEvent(
                    step="Agent 决策",
                    detail=f"调用工具：{tool_name}；参数：{tool_args}",
                )
            )

        if getattr(message, "type", "") == "tool":
            tool_name = getattr(message, "name", "工具")
            tool_result = str(message.content)

            if len(tool_result) > 300:
                tool_result = tool_result[:300] + "…"

            trace.append(
                TraceEvent(
                    step="工具返回",
                    detail=f"{tool_name}：{tool_result}",
                )
            )

    if not trace:
        trace.append(
            TraceEvent(
                step="直接回答",
                detail="本轮回答没有调用业务工具。",
            )
        )

    trace.append(
        TraceEvent(
            step="完成",
            detail="Agent 已生成本轮答复。",
        )
    )

    return trace


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    question = request.message.strip()
    session_id = request.session_id.strip()

    if not question:
        raise HTTPException(status_code=400, detail="问题不能为空。")

    if not session_id:
        raise HTTPException(status_code=400, detail="会话编号不能为空。")

    try:
        with SESSIONS_LOCK:
            history = list(SESSIONS.get(session_id, []))
            active_order_id = SESSION_ORDER_IDS.get(session_id)

        # 识别用户本轮提供的新订单号。
        order_match = ORDER_ID_PATTERN.search(question)
        supplied_order_id = order_match.group(1) if order_match else None

        if supplied_order_id:
            active_order_id = supplied_order_id
            with SESSIONS_LOCK:
                SESSION_ORDER_IDS[session_id] = supplied_order_id

        asks_to_lookup = any(word in question for word in ORDER_LOOKUP_WORDS)
        refers_to_order = any(
            word in question for word in ORDER_REFERENCE_WORDS
        )
        assistant_was_waiting = was_asked_for_order_id(history)

        # 用户只是提供订单号，客服并未在等待订单号时，先确认并询问需求。
        if (
            supplied_order_id
            and not asks_to_lookup
            and not assistant_was_waiting
        ):
            answer = (
                f"收到，我记下本次会话中的订单号是 {supplied_order_id}。"
                "您希望我帮您查询订单状态，还是处理其他问题？"
            )

            new_messages = [
                HumanMessage(content=question),
                AIMessage(content=answer),
            ]
            save_session(session_id, history + new_messages)

            return ChatResponse(
                answer=answer,
                trace=[
                    TraceEvent(
                        step="会话信息",
                        detail=f"已在当前会话中记录订单号：{supplied_order_id}",
                    ),
                    TraceEvent(
                        step="完成",
                        detail="已确认收到订单号，并询问用户下一步需求。",
                    ),
                ],
            )

        agent_question = question

        # 用户用“它”“这个订单”等说法追问时，关联本会话的订单号。
        if (
            active_order_id
            and refers_to_order
            and not supplied_order_id
        ):
            agent_question = (
                f"{question}\n\n"
                f"当前会话关联的订单号是 {active_order_id}。"
                f"请将用户提到的订单理解为 {active_order_id}，"
                "并根据订单查询工具返回的结果回答。"
            )

        # 客服刚索要订单号，用户现在只发号码时，继续查询。
        if (
            supplied_order_id
            and assistant_was_waiting
            and not asks_to_lookup
        ):
            agent_question = (
                f"请查询订单状态。用户刚提供的订单号是 {supplied_order_id}。"
            )

        input_messages = history + [
            HumanMessage(content=agent_question)
        ]

        result = graph.invoke({"messages": input_messages})
        messages = result["messages"]

        answer = messages[-1].content
        if not isinstance(answer, str):
            answer = str(answer)

        if not answer.strip():
            answer = (
                f"我看到您刚才说：“{question}”。"
                "您希望我接下来帮您查询订单、咨询售后政策，还是了解商品信息？"
            )
            messages[-1] = AIMessage(content=answer)

        current_messages = messages[len(history):]
        trace = make_trace(current_messages)
        save_session(session_id, messages)

        return ChatResponse(answer=answer, trace=trace)

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="客服处理问题时发生错误，请检查 Ollama 服务和项目终端日志。",
        )
