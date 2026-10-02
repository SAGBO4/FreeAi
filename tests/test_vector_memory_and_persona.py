"""Tests for EphemeralVectorMemory and ConversationalPersona.
Ensures FreeAI has human personality, conversational warmth, and vector memory recall.
"""

import asyncio
from app.memory.vector_memory import EphemeralVectorMemory
from app.cognition.persona import ConversationalPersona
from app.llm.engine import FreeAIEngine


def test_vector_memory_seeding_and_search():
    vmem = EphemeralVectorMemory()
    # Check that foundational memories exist
    assert len(vmem.memories) >= 3

    # Search for creator
    results = vmem.search_relevant_memories("qui est ton créateur Michael ?", top_k=2)
    assert len(results) > 0
    assert any("Michael SAGBO" in r["text"] for r in results)

    # Search for personality
    results_persona = vmem.search_relevant_memories("parle-moi de ta personnalité", top_k=2)
    assert len(results_persona) > 0
    assert any("personnalité humaine" in r["text"] for r in results_persona)


def test_vector_memory_add_and_context():
    vmem = EphemeralVectorMemory()
    vmem.add_memory("Michael aime développer des applications de cybersécurité en Python.", topic="preference", tags=["python", "cyber"])

    ctx = vmem.get_conversational_context("python cybersécurité")
    assert "Michael aime développer" in ctx


def test_conversational_persona_greetings():
    async def run():
        persona = ConversationalPersona()
        res = await persona.chat("Comment vas-tu ?")
        assert res["success"] is True
        assert res["conversational"] is True
        # Must NOT be a cold machine output
        assert "Objectif traité" not in res["output"]
        assert any(w in res["output"].lower() for w in ["bien", "forme", "journée", "michael", "ami"])
    asyncio.run(run())


def test_conversational_persona_identity():
    async def run():
        persona = ConversationalPersona()
        res = await persona.chat("Qui es-tu ?")
        assert res["success"] is True
        assert "FreeAI" in res["output"]
        assert "compagnon" in res["output"].lower() or "bras droit" in res["output"].lower()
    asyncio.run(run())


def test_llm_engine_routes_conversational_intent():
    engine = FreeAIEngine()
    plan = engine.reason_and_plan("Fréaï, comment vas-tu? Ça va très bien, dis-moi.", {})
    assert plan["domain"] == "conversation"
    assert plan["intent"] == "human_dialogue"

    plan_salut = engine.reason_and_plan("salut jarvis comment tu vas", {})
    assert plan_salut["domain"] == "conversation"
