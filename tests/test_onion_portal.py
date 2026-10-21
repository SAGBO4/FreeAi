import os
import shutil
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


def test_launch_tor_daemon_reports_pending_instead_of_fake_address(tmp_path, monkeypatch):
    """Exécute réellement _launch_tor_daemon (non mocké) quand ni 'tor' ni docker ne sont
    disponibles. Régression ciblée : l'ancien code fabriquait une adresse
    'sovereign_<hex aléatoire>.onion' dans ce cas. Le code corrigé doit laisser
    onion_address à None et exposer bootstrap_pending=True, sans rien inventer."""
    async def _test():
        portal = SovereignOnionPortal()
        portal.RAM_DIR = str(tmp_path / "freeai_onion")

        # Simule un hôte sans binaire 'tor' et sans Docker fonctionnel
        monkeypatch.setattr(shutil, "which", lambda name: None)

        async def fail_docker(*args, **kwargs):
            raise FileNotFoundError("docker not available in this test")
        monkeypatch.setattr(asyncio, "create_subprocess_exec", fail_docker)

        # Évite d'attendre réellement les ~10s de polling du fichier hostname
        monkeypatch.setattr(asyncio, "sleep", AsyncMock())

        portal._ensure_ram_dir()
        torrc_path = f"{portal.RAM_DIR}/torrc"
        with open(torrc_path, "w", encoding="utf-8") as f:
            f.write("")

        await portal._launch_tor_daemon(torrc_path)

        assert portal.onion_address is None
        assert portal.bootstrap_pending is True

        # Simule l'état "actif" pour vérifier le message honnête de get_status
        portal.is_active = True
        status = portal.get_status()
        assert status["bootstrap_pending"] is True
        assert ".onion" not in status["onion_address"]
        assert "attente" in status["onion_address"].lower()

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
