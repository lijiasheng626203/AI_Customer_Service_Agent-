# Agent 配置

AGENT_NAME = "E-Commerce Customer Service Agent"

AGENT_DESCRIPTION = """
这是一个基于 LangChain 和 LangGraph 的电商客服 Agent。

主要功能：
1. 查询订单状态
2. 查询商品价格和库存
3. 查询售后问题
4. 检索客服知识库
5. 根据用户问题自动选择合适的工具
"""

AVAILABLE_TOOLS = [
    "订单查询",
    "商品查询",
    "售后查询",
    "RAG知识库"
]