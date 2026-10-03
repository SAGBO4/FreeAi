import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

from app.network.resilience import NetworkResilience

@pytest.fixture
def network_resilience():
    telegram_mock = AsyncMock()
    with patch.object(NetworkResilience, '_check_command', return_value=False):
        nr = NetworkResilience(telegram_vault=telegram_mock)
    return nr

def test_check_connectivity_online(network_resilience):
    async def run_test():
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        
        mock_client_instance = AsyncMock()
        mock_client_instance.get.return_value = mock_resp
        
        mock_client_class = MagicMock()
        mock_client_class.__aenter__.return_value = mock_client_instance
        mock_client_class.__aexit__ = AsyncMock()
        
        with patch('httpx.AsyncClient', return_value=mock_client_class):
            status = await network_resilience.check_connectivity()
            assert status["online"] is True
            assert status["latency_ms"] >= 0.0
    asyncio.run(run_test())

def test_check_connectivity_offline(network_resilience):
    async def run_test():
        mock_client_instance = AsyncMock()
        mock_client_instance.get.side_effect = Exception("Connection Failed")
        
        mock_client_class = MagicMock()
        mock_client_class.__aenter__.return_value = mock_client_instance
        mock_client_class.__aexit__ = AsyncMock()
        
        with patch('httpx.AsyncClient', return_value=mock_client_class):
            status = await network_resilience.check_connectivity()
            assert status["online"] is False
            assert status["latency_ms"] == 0.0
    asyncio.run(run_test())

def test_cascade_fallback_no_adb(network_resilience):
    async def run_test():
        network_resilience._adb_available = False
        network_resilience._nmcli_available = False
        
        with patch.object(network_resilience, 'trigger_cloud_mode', AsyncMock()) as mock_trigger:
            active_interface = await network_resilience.cascade_fallback()
            assert active_interface == "cloud_only"
            mock_trigger.assert_called_once()
    asyncio.run(run_test())

def test_on_connectivity_restored(network_resilience):
    async def run_test():
        network_resilience.cloud_mode_active = True
        network_resilience.active_interface = "cloud_only"
        
        await network_resilience.on_connectivity_restored()
        
        assert network_resilience.cloud_mode_active is False
        assert network_resilience.active_interface == "wifi"
        network_resilience.telegram_vault.send_message.assert_called_once_with("📡 Connexion restaurée ! Resync en cours...")
    asyncio.run(run_test())

def test_get_status_structure(network_resilience):
    network_resilience.is_online = True
    network_resilience.last_latency_ms = 42.5
    network_resilience.active_interface = "hotspot"
    network_resilience.cloud_mode_active = False
    network_resilience.uptime_percentage = 99.9
    network_resilience.disconnection_count = 1
    network_resilience._adb_available = True
    
    status = network_resilience.get_status()
    
    assert "online" in status
    assert status["online"] is True
    assert "latency_ms" in status
    assert status["latency_ms"] == 42.5
    assert "active_interface" in status
    assert status["active_interface"] == "hotspot"
    assert "cloud_mode" in status
    assert status["cloud_mode"] is False
    assert "uptime_pct" in status
    assert status["uptime_pct"] == 99.9
    assert "disconnections_count" in status
    assert status["disconnections_count"] == 1
    assert "adb_available" in status
    assert status["adb_available"] is True
