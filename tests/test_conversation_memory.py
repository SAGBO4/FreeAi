import pytest
from app.cognition.conversation_memory import ConversationMemory
from app.cognition.persona import ConversationalPersona
from unittest.mock import patch, MagicMock

def test_add_and_retrieve_turns():
    mem = ConversationMemory()
    for i in range(5):
        mem.add_turn('user', f'Msg {i}')
    history = mem.get_history_for_llm(max_turns=15)
    assert len(history) == 5
    assert history[0]['content'] == 'Msg 0'
    assert history[-1]['content'] == 'Msg 4'

def test_sliding_window():
    mem = ConversationMemory()
    for i in range(25):
        mem.add_turn('user', f'Msg {i}')
    history = mem.get_history_for_llm(max_turns=15)
    assert len(history) == 15
    assert history[0]['content'] == 'Msg 10'
    assert history[-1]['content'] == 'Msg 24'

def test_tag_detection():
    mem = ConversationMemory()
    assert mem.is_tagged_mention('@LesaintAi_bot bonjour') is True
    assert mem.is_tagged_mention('bonjour') is False
    assert mem.is_tagged_mention('Salut @lesaintai_bot!') is True

def test_memorize_heuristic():
    mem = ConversationMemory()
    assert mem.should_memorize_long_term('Michael', 'Je préfère Python') is True
    assert mem.should_memorize_long_term('ok', 'ça marche') is False
    assert mem.should_memorize_long_term('On part sur cette architecture', 'Parfait') is True

def test_gzip_serialization():
    mem = ConversationMemory()
    mem.add_turn('user', 'Salut')
    mem.add_turn('assistant', 'Hello')
    
    data = mem.serialize_to_gzip()
    assert isinstance(data, bytes)
    
    mem2 = ConversationMemory.restore_from_gzip(data)
    assert mem2.turn_count == 2
    assert mem2.turns[0]['content'] == 'Salut'
    assert mem2.turns[1]['content'] == 'Hello'

import asyncio

def test_persona_multiturn():
    async def run():
        persona = ConversationalPersona()
        persona.groq_api_key = "fake_key"
        
        with patch.object(persona, '_query_groq_persona', return_value="Réponse"):
            await persona.chat("Message 1")
            await persona.chat("Message 2")
            await persona.chat("Message 3")
            
            history = persona.conv_memory.get_history_for_llm()
            assert len(history) == 6
            assert history[0]['content'] == "Message 1"
            assert history[2]['content'] == "Message 2"
            assert history[4]['content'] == "Message 3"
    asyncio.run(run())

def test_persona_uses_conv_memory():
    async def run():
        persona = ConversationalPersona()
        persona.groq_api_key = "" # Trigger local reply
        
        assert persona.conv_memory.turn_count == 0
        await persona.chat("Comment vas-tu ?")
        assert persona.conv_memory.turn_count == 2
    asyncio.run(run())
