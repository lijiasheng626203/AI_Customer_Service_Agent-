from langchain_core.tools import tool


@tool
def query_product(product_name: str) -> str:
    """查询商品的价格和库存信息，需要提供商品名称。"""

    products = {
        "iPhone 15": "价格：4999元，库存：有货。",
        "MacBook Air": "价格：7999元，库存：有货。",
        "AirPods Pro": "价格：1899元，库存：库存不足。",
    }

    return products.get(
        product_name,
        "没有找到该商品，请检查商品名称。"
    )