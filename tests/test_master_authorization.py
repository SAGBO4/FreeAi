import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

from app.memory.telegram_vault import TelegramNeuralVault
from app.security.active_defense import ActiveDefenseSentinel, AttackVector

@pytest.fixture
def telegram_vault():
    vault = TelegramNeuralVault(token="test_token", chat_id="6149977795")
    vault.master_user_id = "6149977795"
    vault.send_message = AsyncMock(return_value=True)
    vault._persist_group_chat_id = MagicMock()
    vault._persist_new_chat_id = MagicMock()
    return vault

class MockResponse:
    def __init__(self, json_data, status_code=200):
        self.status_code = status_code
        self._json = json_data
    def json(self):
        return self._json
    @property
    def text(self):
        return str(self._json)

@pytest.mark.anyio
async def test_master_user_recognition(telegram_vault):
    # Ensure ID 6149977795 is always recognized
    assert telegram_vault.is_master_user("6149977795") == True
    assert telegram_vault.is_master_user(6149977795) == True
    assert telegram_vault.is_master_user("unknown", username="speedylesaint") == True
    assert telegram_vault.is_master_user("unknown", username="SAGBO4") == True
    assert telegram_vault.is_master_user("12345", username="attacker") == False

@pytest.mark.anyio
async def test_group_message_from_master_not_blocked(telegram_vault):
    # Simulate a message from Michael in a group chat (-100123456789)
    # the group_chat_id should be stored, and no alert should be sent.
    
    msg = {
        "message_id": 1,
        "chat": {"id": -100123456789, "type": "supergroup"},
        "from": {"id": 6149977795, "username": "SpeedyLesaint"},
        "text": "/setup_hq"
    }
    
    updates_mock = {"result": [{"update_id": 1, "message": msg}]}
    
    mock_client = MagicMock()
    mock_client.get = AsyncMock(return_value=MockResponse(updates_mock))
    mock_client.post = AsyncMock(return_value=MockResponse({"ok": True}))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    
    with patch("httpx.AsyncClient", return_value=mock_client):
        with patch.object(telegram_vault, "setup_community_hq", new_callable=AsyncMock) as mock_setup:
            mock_setup.return_value = {"success": True, "total_created": 6}
            
            await telegram_vault.poll_incoming_command()
            
            # Should have remembered the group chat id
            assert str(telegram_vault.group_chat_id) == "-100123456789"
            
            # Setup HQ should be called
            mock_setup.assert_called_once_with(target_chat_id="-100123456789")
            
            # Confirmation message should be sent
            telegram_vault.send_message.assert_called_once()
            args, kwargs = telegram_vault.send_message.call_args
            assert "Quartier Général Configuré" in args[0]

@pytest.mark.anyio
async def test_private_message_attacker_blocked(telegram_vault):
    # Attacker in private chat
    msg = {
        "message_id": 2,
        "chat": {"id": 999999, "type": "private"},
        "from": {"id": 999999, "username": "attacker"},
        "text": "hello"
    }
    
    updates_mock = {"result": [{"update_id": 2, "message": msg}]}
    
    mock_client = MagicMock()
    mock_client.get = AsyncMock(return_value=MockResponse(updates_mock))
    mock_client.post = AsyncMock(return_value=MockResponse({"ok": True}))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    
    with patch("httpx.AsyncClient", return_value=mock_client):
        res = await telegram_vault.poll_incoming_command()
        assert res is None # Should block
        
        # Intrusion alert sent to master chat_id
        mock_client.post.assert_called_once()
        args, kwargs = mock_client.post.call_args
        assert kwargs["json"]["chat_id"] == "6149977795"
        assert "Tentative d'intrusion interceptée" in kwargs["json"]["text"]

@pytest.mark.anyio
async def test_active_defense_allows_master():
    defense = ActiveDefenseSentinel()
    
    # Simulate flood from master
    for i in range(25):
        defense.detect_flood("master_or_gateway")
        
    is_safe, msg = await defense.audit_and_defend_request("master_or_gateway", "hello")
    assert is_safe == True # Master is not blocked by flood

    # Simulated flood from unknown
    for i in range(25):
        defense.detect_flood("192.168.1.100")
        
    is_safe, msg = await defense.audit_and_defend_request("192.168.1.100", "hello")
    assert is_safe == False # Unknown is blocked by flood
    assert "FLOOD DÉTECTÉ" in msg


@pytest.mark.anyio
async def test_community_guide_content(telegram_vault):
    guide = telegram_vault.get_community_guide_text()
    assert "GUIDE OFFICIEL FREEAI SOUVERAIN" in guide
    assert "freeAi" in guide
    assert "lesaintAi" in guide
    assert "/clean_hq" in guide
    assert "/career" in guide
    assert "/birthday" in guide
    assert "/defense" in guide
    assert "/ui" in guide


@pytest.mark.anyio
async def test_clean_duplicate_topics_flow(telegram_vault):
    msg = {
        "message_id": 10,
        "chat": {"id": -100998877, "type": "supergroup"},
        "from": {"id": 6149977795, "username": "SpeedyLesaint"},
        "text": "nettoie moi les doublons"
    }
    updates_mock = {"result": [{"update_id": 10, "message": msg}]}
    
    mock_client = MagicMock()
    mock_client.get = AsyncMock(return_value=MockResponse(updates_mock))
    mock_client.post = AsyncMock(return_value=MockResponse({"ok": True}))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    
    with patch("httpx.AsyncClient", return_value=mock_client):
        with patch.object(telegram_vault, "clean_duplicate_topics", new_callable=AsyncMock) as mock_clean:
            mock_clean.return_value = {"success": True, "deleted_count": 4, "total_canonical": 6}
            
            await telegram_vault.poll_incoming_command()
            mock_clean.assert_called_once_with(target_chat_id="-100998877")
            assert telegram_vault.send_message.call_count >= 2

