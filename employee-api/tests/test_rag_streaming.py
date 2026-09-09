import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from app.schemas.rag import QuestionRequest
from app.services.rag import RAGService
from app.services.ai_agent import AIAgentService


class TestStreamingRAG(unittest.TestCase):
    def test_question_request_schema(self):
        req_default = QuestionRequest(question="How to store goods?")
        self.assertFalse(req_default.stream)

        req_stream = QuestionRequest(question="How to store goods?", stream=True)
        self.assertTrue(req_stream.stream)

    @patch("app.services.rag.create_embedding")
    @patch("app.services.rag.client")
    def test_rag_service_ask_stream(self, mock_client, mock_create_embedding):
        mock_db = MagicMock()
        service = RAGService(mock_db)

        # Mock repository search returning no results
        service.repository.search = AsyncMock(return_value=[])

        async def run_test():
            chunks = []
            async for chunk in service.ask_stream("Unknown query?"):
                chunks.append(chunk)
            return "".join(chunks)

        result = asyncio.run(run_test())
        self.assertIn("I don't know", result)

    @patch("app.services.ai_agent.client")
    def test_ai_agent_service_ask_stream(self, mock_client):
        inventory_mock = MagicMock()
        rag_mock = MagicMock()
        order_mock = MagicMock()

        agent = AIAgentService(inventory_mock, rag_mock, order_mock)

        mock_choice = MagicMock()
        mock_choice.message.tool_calls = None
        mock_choice.message.content = "Normal response"

        mock_client.chat.completions.create.side_effect = [
            MagicMock(choices=[mock_choice]),  # First call (tool check)
            [
                MagicMock(choices=[MagicMock(delta=MagicMock(content="Hello "))]),
                MagicMock(choices=[MagicMock(delta=MagicMock(content="world!"))]),
            ],  # Stream call
        ]

        async def run_test():
            chunks = []
            async for chunk in agent.ask_stream("Hello?"):
                chunks.append(chunk)
            return "".join(chunks)

        result = asyncio.run(run_test())
        self.assertEqual(result, "Hello world!")


if __name__ == "__main__":
    unittest.main()
