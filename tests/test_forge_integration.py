import pytest
from app.forge.bridge import ForgeBridge
from app.orchestrator.orchestrator import TechLeadOrchestrator
from app.tools.gateway import ToolGateway
from app.resource_manager.watchdog import ResourceManager


def test_forge_bridge_status():
    """Vérifie la détection et le statut de la machine Forge et de Craft-Suite."""
    bridge = ForgeBridge()
    st = bridge.get_status()
    assert st["forge_installed"]
    assert st["craft_installed"]
    assert st["forge_skills_count"] >= 8
    assert st["craft_skills_count"] >= 100
    assert "pytest" in st["test_runners"]


def test_forge_tamper_check():
    """Vérifie le contrôle anti-altération des tests (tamper_check.py)."""
    bridge = ForgeBridge()
    res = bridge.run_tamper_check(base_commit="HEAD")
    assert res.get("success")
    assert res.get("clean")
    assert res.get("findings_count") == 0


def test_forge_verified_task_execution():
    """Vérifie le cycle en 5 étapes de Forge."""
    bridge = ForgeBridge()
    res = bridge.execute_verified_code_task(
        feature_name="Test Authentication Module",
        specification="Implémenter JWT sans faille de désérialisation"
    )
    assert res["success"]
    assert len(res["stages"]) == 5
    assert res["stages"][0]["stage"] == "1. spec_intake"
    assert res["stages"][1]["stage"] == "2. test_authoring"


def test_orchestrator_code_agent_forge_integration(tmp_path):
    """Vérifie que CodeAgent dans TechLeadOrchestrator utilise la machine Forge."""
    import asyncio
    gw = ToolGateway(workspace_root=str(tmp_path), mode="freeAi")
    rm = ResourceManager()
    tech_lead = TechLeadOrchestrator(tool_gateway=gw, resource_manager=rm)

    assert tech_lead.forge.is_forge_installed

    async def _run():
        res = await tech_lead.code_agent.execute_task(
            "Synthesize Cryptographic Module",
            {"context": "testing"}
        )
        assert res["status"] == "success"
        assert "Forge" in res["methodology"]
        assert len(res["forge_cycle"]) == 5

    asyncio.run(_run())
