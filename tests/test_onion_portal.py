import os
import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from app.network.onion_portal import SovereignOnionPortal
from app.orchestrator.orchestrator import TechLeadOrchestrator
from app.tools.gateway import ToolGateway
from app.resource_manager.watchdog import ResourceManager


def test_onion_portal_permission_denied_in_freeai():
    """Vérifie que l'activation du portail Tor Onion V3 est strictement bloquée en mode freeAi (Sudo requis)."""
    async def _test():
        portal = SovereignOnionPortal()
        with pytest.raises(PermissionError) as exc_info:
            await portal.start_portal(mode="freeAi")
        assert "ACCÈS REFUSÉ" in str(exc_info.value)
        assert not portal.is_active

    asyncio.run(_test())


def test_onion_portal_status_and_defaults():
    """Vérifie l'état initial et la conformité Mode NÉANT (stockage /dev/shm)."""
    portal = SovereignOnionPortal()
    st = portal.get_status()
    assert not st["is_active"]
    assert "/dev/shm" in st["storage_layer"]
    assert "lesaintAi" in st["mode_restriction"]
    assert "Inviolable" in st["sacred_life_sentinel"]


def test_onion_portal_start_and_stop_in_lesaint_mode(monkeypatch):
    """Vérifie le démarrage en mode lesaintAi, la génération de token et la purge de RAM à l'arrêt."""
    async def _test():
        portal = SovereignOnionPortal()

        # Mock the internal tor launcher to prevent blocking circuit bootstrap in test
        async def mock_launch(path):
            portal.onion_address = "sovereign_test_node_ed25519.onion"

        monkeypatch.setattr(portal, "_launch_tor_daemon", mock_launch)

        st = await portal.start_portal(mode="lesaintAi")
        assert portal.is_active
        assert portal.auth_token is not None
        assert len(portal.auth_token) >= 32
        assert "sovereign" in st["onion_address"]

        # Verify stop clears everything
        stopped = await portal.stop_portal()
        assert stopped
        assert not portal.is_active
        assert portal.auth_token is None
        assert portal.onion_address is None

    asyncio.run(_test())


def test_orchestrator_onion_integration(tmp_path):
    """Vérifie l'intégration du portail Onion dans l'orchestrateur TechLead."""
    async def _test():
        gw = ToolGateway(workspace_root=str(tmp_path), mode="lesaintAi", allow_sudo=True)
        rm = ResourceManager()
        tech_lead = TechLeadOrchestrator(tool_gateway=gw, resource_manager=rm)
        tech_lead.set_mode("lesaintAi")

        status = tech_lead.get_onion_portal_status()
        assert not status["is_active"]
        assert status["port"] == SovereignOnionPortal.DEFAULT_PORT

        # Mock portal daemon launch
        async def mock_launch(path):
            tech_lead.onion_portal.onion_address = "test_lead_node.onion"

        tech_lead.onion_portal._launch_tor_daemon = mock_launch

        res = await tech_lead.start_onion_portal()
        assert res["is_active"]
        assert tech_lead.onion_portal.is_active

        # Switching back to freeAi must automatically kill the onion portal
        tech_lead.set_mode("freeAi")
        await asyncio.sleep(0.05)
        await tech_lead.stop_onion_portal()
        assert not tech_lead.onion_portal.is_active

    asyncio.run(_test())
