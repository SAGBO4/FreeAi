import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from app.memory.telegram_vault import TelegramNeuralVault
import logging
import httpx

logging.basicConfig(level=logging.DEBUG)

async def main():
    telegram_vault = TelegramNeuralVault(token="test_token", chat_id="6149977795")
    telegram_vault.master_user_id = "6149977795"
    telegram_vault.send_message = AsyncMock(return_value=True)
    msg = {
        "message_id": 1,
        "chat": {"id": -100123456789, "type": "supergroup"},
        "from": {"id": 6149977795, "username": "SpeedyLesaint"},
        "text": "/setup_hq"
    }
    updates_mock = {"result": [{"update_id": 1, "message": msg}]}
    
    class MockResponse:
        def __init__(self, json_data):
            self.status_code = 200
            self._json = json_data
        def json(self):
            return self._json

    mock_client = MagicMock()
    mock_client.get = AsyncMock(return_value=MockResponse(updates_mock))
    mock_client.post = AsyncMock(return_value=MockResponse({"ok": True}))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    
    with patch("httpx.AsyncClient", return_value=mock_client):
        with patch.object(telegram_vault, "setup_community_hq", new_callable=AsyncMock) as mock_setup:
            mock_setup.return_value = {"success": True, "total_created": 6}
            res = await telegram_vault.poll_incoming_command()
            print("group_chat_id:", telegram_vault.group_chat_id)
            print("returned command:", res)

asyncio.run(main())
