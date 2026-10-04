import os
import shutil
import pytest
from pathlib import Path
from app.tools.gateway import ToolGateway
from app.tools.design_bridge import DesignSystemBridge
from app.agents.ui_ux_agent import UiUxAgent


def test_design_bridge_domains_matrix():
    bridge = DesignSystemBridge()
    domains = bridge.list_domains()
    assert len(domains) >= 10

    domain_keys = [d["key"] for d in domains]
    assert "crypto" in domain_keys
    assert "finance" in domain_keys
    assert "payment" in domain_keys
    assert "ai-chat" in domain_keys
    assert "ecommerce" in domain_keys
    assert "crm" in domain_keys
    assert "project-management" in domain_keys

    # Check that crypto and finance are available locally
    crypto_meta = next(d for d in domains if d["key"] == "crypto")
    assert crypto_meta["available"] is True
    assert "trading-card" in crypto_meta["components"]


def test_design_bridge_domain_resolution():
    bridge = DesignSystemBridge()
    assert bridge.resolve_domain("crypto") == "crypto"
    assert bridge.resolve_domain("blockchain wallet tracker") == "crypto"
    assert bridge.resolve_domain("bourse trading et kpi") == "finance"
    assert bridge.resolve_domain("assistant ai chat agent") == "ai-chat"
    assert bridge.resolve_domain("gestion de prospects leads et crm") == "crm"
    assert bridge.resolve_domain("boutique ecommerce panier") == "ecommerce"


def test_design_bridge_inspect_domain_template():
    bridge = DesignSystemBridge()
    info = bridge.inspect_domain_template("crypto")
    assert info["success"] is True
    assert info["domain"] == "crypto"
    assert "page.tsx" in info["files"]
    assert "components/trading-card.tsx" in info["files"]
    assert len(info["required_ui_primitives"]) > 0
    # Must detect button or card or tabs
    assert any(p in info["required_ui_primitives"] for p in ("button", "card", "tabs", "select"))


def test_design_bridge_adapt_and_copy_template(tmp_path):
    bridge = DesignSystemBridge()
    target_dir = tmp_path / "mock_project"

    manifest = bridge.adapt_and_copy_template(
        domain_key="crypto",
        target_dir=str(target_dir),
        app_title="Apex Crypto Portal"
    )

    assert manifest["success"] is True
    assert manifest["domain"] == "crypto"
    assert len(manifest["copied_domain_files"]) >= 5
    assert len(manifest["copied_ui_primitives"]) >= 1

    # Check files exist on destination
    assert (target_dir / "app" / "crypto" / "page.tsx").exists()
    assert (target_dir / "components" / "ui").exists()
    assert (target_dir / "lib" / "utils.ts").exists()

    # Check title customization in page.tsx
    page_content = (target_dir / "app" / "crypto" / "page.tsx").read_text(encoding="utf-8")
    assert "Apex Crypto Portal" in page_content


def test_ui_ux_agent_execution(tmp_path):
    import asyncio

    async def _run():
        gateway = ToolGateway(workspace_root=Path("/home/lesaint/Rendue/FreeAi"))
        agent = UiUxAgent(tool_gateway=gateway)

        target_dir = tmp_path / "trading_app"
        result = await agent.execute_task(
            task_description="Créer une interface de trading crypto et gestion de wallet blockchain",
            context={"target_dir": str(target_dir), "app_title": "Jarvis Crypto Terminal"}
        )

        assert result["status"] == "success"
        assert result["domain_resolved"] == "crypto"
        assert result["adaptation_manifest"] is not None
        assert result["adaptation_manifest"]["success"] is True
        assert (target_dir / "app" / "crypto" / "page.tsx").exists()
        assert "innovation_touch" in result
        assert "Web3" in result["innovation_touch"] or "ticker" in result["innovation_touch"]

    asyncio.run(_run())
