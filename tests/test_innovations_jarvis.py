import pytest
import os
import json
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch

from app.cognition.conversation_memory import ConversationMemory
from app.cognition.persona import ConversationalPersona
from app.cognition.emoji_router import classify_response_emoji
from app.orchestrator.orchestrator import TechLeadOrchestrator
import cli

def test_innovation_1_temporal():
    asyncio.run(_test_innovation_1_temporal())

async def _test_innovation_1_temporal():
    mem = ConversationMemory()
    temp_ctx = mem.get_temporal_context()
    assert any(x in temp_ctx for x in ["22h00-06h00", "06h00-09h00", "09h00-18h00", "18h00-22h00"])
    
    with patch('app.cognition.persona.httpx.AsyncClient') as mock_client:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"choices": [{"message": {"content": "Test"}}]}
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_resp)
        
        persona = ConversationalPersona(conv_memory=mem)
        await persona._query_groq_persona("Hello", "Context")
        
        call_args = mock_client.return_value.__aenter__.return_value.post.call_args
        if call_args:
            payload = call_args[1]["json"]
            sys_msg = payload["messages"][0]["content"]
            assert "Contexte temporel" in sys_msg

def test_innovation_2_semantic_summary():
    mem = ConversationMemory()
    mem.update_topic_summary("Je veux une architecture en microservices", "C'est noté, je prépare ça.")
    summary = mem.get_topic_summary_for_prompt()
    assert "Sujets clés" in summary
    assert len(mem.topic_summary) == 1
    
    for i in range(10):
        mem.update_topic_summary(f"Question {i}", f"Reponse {i}")
    assert len(mem.topic_summary) == 5

def test_innovation_3_and_5_smart_telegram_send():
    asyncio.run(_test_innovation_3_and_5_smart_telegram_send())

async def _test_innovation_3_and_5_smart_telegram_send():
    vault = MagicMock()
    vault.send_message = AsyncMock()
    vault.send_reply = AsyncMock()
    
    cmd = MagicMock()
    cmd.message_id = 1234
    
    # Short message
    await cli._smart_telegram_send(vault, "Test message", cmd)
    assert vault.send_message.called
    assert not vault.send_reply.called
    sent_text = vault.send_message.call_args[0][0]
    assert sent_text.startswith("💬") or "Test message" in sent_text
    
    # Long message
    vault.send_message.reset_mock()
    vault.send_reply.reset_mock()
    long_msg = "A" * 301
    await cli._smart_telegram_send(vault, long_msg, cmd)
    assert vault.send_reply.called
    assert not vault.send_message.called
    
    # Code formatting
    vault.send_message.reset_mock()
    vault.send_reply.reset_mock()
    code_msg = "Voici: ```python\\nprint(1)\\n```"
    await cli._smart_telegram_send(vault, code_msg, cmd)
    sent_text = vault.send_message.call_args[0][0]
    assert "<pre><code>" in sent_text or "<code>" in sent_text

def test_innovation_4_prewarm():
    import shutil
    os.makedirs("jarvis_memory", exist_ok=True)
    with open("jarvis_memory/test1.json", "w") as f:
        json.dump([{"prompt": "A", "response": "B"}], f)
        
    with patch('app.orchestrator.orchestrator.TechLeadOrchestrator.__init__', return_value=None):
        orchestrator = TechLeadOrchestrator()
        orchestrator.vector_memory = MagicMock()
        TechLeadOrchestrator._prewarm_from_cloud_bootstrap(orchestrator)
        assert orchestrator.vector_memory.add_memory.called
        
    shutil.rmtree("jarvis_memory", ignore_errors=True)

def test_innovation_5_emoji():
    assert classify_response_emoji("Voici le code Python") == "💻"
    assert classify_response_emoji("Erreur fatale !") == "🚨"
    assert classify_response_emoji("Je suis Jarvis") == "🤖"
    assert classify_response_emoji("Nouvelle idée de génie") == "🧠"
