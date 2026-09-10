import asyncio
from typing import TypedDict, Annotated
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI
from langchain.tools import tool

from app.database import SessionLocal
from app.config import settings
from app.services.inventory import InventoryService
from app.services.order import OrderService
from app.services.rag import RAGService
import app.models.user  # noqa: F401 - ensure SQLAlchemy models are registered


# 1. Define Agent State
class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    llm_calls: int


async def main():
    async with SessionLocal() as db:
        # Initialize business services backed by DB
        inventory_svc = InventoryService(db)
        order_svc = OrderService(db)
        rag_svc = RAGService(db)

        # Wrap service methods into LangChain tools
        tools = [
            tool(inventory_svc.get_inventory),
            tool(order_svc.get_order_status),
            tool(rag_svc.search_warehouse_policy),
        ]

        # Initialize LLM & bind tools
        model = ChatOpenAI(
            model="qwen/qwen3.6-27b",
            openai_api_key=settings.openai_api_key,
            openai_api_base=settings.openai_base_url,
            max_completion_tokens=500,
        )
        model_with_tools = model.bind_tools(tools)

        # 2. Define Node Functions
        async def llm_call(state: AgentState):
            response = await model_with_tools.ainvoke(state["messages"])
            return {
                "messages": [response],
                "llm_calls": state.get("llm_calls", 0) + 1,
            }

        tool_node = ToolNode(tools)

        # 3. Define Routing Logic
        def should_continue(state: AgentState):
            last_message = state["messages"][-1]
            if hasattr(last_message, "tool_calls") and last_message.tool_calls:
                return "tools"
            return END

        # 4. Assemble StateGraph
        workflow = StateGraph(AgentState)

        workflow.add_node("llm", llm_call)
        workflow.add_node("tools", tool_node)

        workflow.add_edge(START, "llm")
        workflow.add_conditional_edges(
            "llm",
            should_continue,
            {
                "tools": "tools",
                END: END,
            },
        )
        workflow.add_edge("tools", "llm")

        # 5. Compile the Graph
        agent = workflow.compile()

        # 6. Run the Agent Graph
        query = "Why hasn't order 1 shipped? Also check inventory for item sku wh-1."
        print(f"User Query: {query}\n" + "=" * 50)

        result = await agent.ainvoke({
            "messages": [{"role": "user", "content": query}],
            "llm_calls": 0,
        })

        print("\n--- Message Trace ---")
        for msg in result["messages"]:
            print(f"[{msg.type.upper()}]: {msg.content}")
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                print(f"  -> Tool Calls: {msg.tool_calls}")

        print("\n" + "=" * 50)
        print(f"Total LLM Calls: {result['llm_calls']}")


if __name__ == "__main__":
    asyncio.run(main())
