from langchain_core.tools import tool


@tool
def query_after_sales(issue: str) -> str:
    """查询商品退货、换货和售后政策。"""

    policies = {
        "退货": "商品签收后7天内，在商品保持完好的情况下可以申请退货。",
        "换货": "商品存在质量问题时，可以申请换货。",
        "退款": "符合退货条件并审核通过后，退款会原路返回。",
        "保修": "电子产品提供一年有限保修服务。",
    }

    for keyword, answer in policies.items():
        if keyword in issue:
            return answer

    return "暂时没有找到相关售后政策，建议联系人工客服进一步处理。"