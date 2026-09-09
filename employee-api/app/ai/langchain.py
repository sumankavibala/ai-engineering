import asyncio
from langchain.agents import create_agent
from app.database import SessionLocal
from app.services.inventory import InventoryService
from app.services.order import OrderService
from app.services.rag import RAGService
import app.models.user  # noqa: F401 - ensure SQLAlchemy models are registered

async def main():
    async with SessionLocal() as db:
        inventory_svc = InventoryService(db)
        order_svc = OrderService(db)
        rag_svc = RAGService(db)

        from langchain_openai import ChatOpenAI
        from app.config import settings

        model = ChatOpenAI(
            model="qwen/qwen3.6-27b",
            openai_api_key=settings.openai_api_key,
            openai_api_base=settings.openai_base_url,
            max_completion_tokens=2000,
        )

        from langchain.tools import tool

        agent = create_agent(
            model=model,
            tools=[
                tool(inventory_svc.get_inventory),
                tool(order_svc.get_order_status),
                tool(rag_svc.search_warehouse_policy),
            ],
            system_prompt="""
            You are a warehouse assistant.
            Use inventory tools for live inventory data.
            Use order tools for live order information.
            Use policy search for warehouse policies.
            Never invent warehouse information.
            """
        )

        result = await agent.ainvoke({
            "messages": [
                {"role": "user", "content": "how many wh-1 units are available?"}
            ]
        })
        print('HumanMessage--->>',result["messages"][-1].content)
        print('---------------------------->>>>>>>>>>>>>>>>>>>>>',result["messages"][-1].tool_calls)


if __name__ == "__main__":
    asyncio.run(main())
