from graph import graph
from langchain_core.messages import HumanMessage


def run_agent():
    print("=" * 50)
    print("      电商客服 AI Agent")
    print("=" * 50)
    print("输入 exit 可以退出")
    print()

    while True:
        question = input("用户：")

        if question.lower() == "exit":
            print("客服：感谢您的使用，再见！")
            break

        if not question.strip():
            continue

        result = graph.invoke({
            "messages": [
                HumanMessage(content=question)
            ]
        })

        print("\nAI客服：")
        print(result["messages"][-1].content)
        print()


if __name__ == "__main__":
    run_agent()