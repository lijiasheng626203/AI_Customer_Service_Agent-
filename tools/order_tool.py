from langchain_core.tools import tool


@tool
def query_order(order_id: str) -> str:
    """查询用户的订单状态，需要提供订单号。"""

    orders = {
        "10001": "订单已经发货，预计明天送达。",
        "10002": "订单正在处理中，预计2天内发货。",
        "10003": "订单已送达。"
    }

    return orders.get(
        order_id,
        "没有找到这个订单，请检查订单号。"
    )
