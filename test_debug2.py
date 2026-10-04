import asyncio
from unittest.mock import AsyncMock, patch
from app.memory.telegram_vault import TelegramNeuralVault
import logging

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
    
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = updates_mock
        mock_get.return_value = mock_response
        
        with patch.object(telegram_vault, "setup_community_hq") as mock_setup:
            mock_setup.return_value = {"success": True, "total_created": 6}
            await telegram_vault.poll_incoming_command()
            print("group_chat_id:", telegram_vault.group_chat_id)

asyncio.run(main())
