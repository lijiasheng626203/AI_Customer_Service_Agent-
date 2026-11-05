import logging
from pathlib import Path

from langchain_core.tools import tool

from rag import retriever


logger = logging.getLogger(__name__)


@tool
def search_knowledge_base(question: str) -> str:
    """检索公司介绍、商品资料、配送和售后政策等本地知识库文档。"""
    question = question.strip()
    if not question:
        return "请先说明要查询的问题。"

    try:
        documents = retriever.invoke(question)
    except Exception:
        logger.exception("知识库检索失败")
        return "知识库检索失败，当前无法核实相关业务信息。"

    results = []
    seen = set()
    for document in documents:
        content = str(document.page_content).strip()
        if not content:
            continue
        metadata = document.metadata or {}
        source = metadata.get("source")
        source_name = Path(str(source)).name if source else "未知文档"
        identity = (source_name, content)
        if identity in seen:
            continue
        seen.add(identity)
        results.append(f"【来源：{source_name}】\n{content}")

    if not results:
        return "知识库没有返回可用资料，当前无法核实这个问题。"

    return (
        "以下是知识库检索到的候选片段。"
        "仅使用片段中明确写出的业务事实回答；"
        "如果片段没有直接回答用户的问题，应说明知识库未提供可靠答案。\n\n"
        + "\n\n".join(results)
    )
