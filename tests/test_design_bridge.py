import io
import pytest
from app.tools.design_bridge import DesignSystemBridge


def test_design_system_bridge_discovery():
    bridge = DesignSystemBridge()
    assert bridge.is_available is True
    comps = bridge.list_components()
    assert len(comps) >= 50
    assert "button" in comps
    assert "card" in comps
    assert "dialog" in comps


def test_design_system_bridge_categories():
    bridge = DesignSystemBridge()
    cats = bridge.get_catalog_by_categories()
    assert "layout" in cats
    assert "inputs" in cats
    assert "overlay" in cats
    assert "button" in cats["inputs"]
    assert "card" in cats["layout"]


def test_design_system_bridge_search():
    bridge = DesignSystemBridge()
    results = bridge.search_components("dia")
    assert any("dialog" in r for r in results)


def test_design_system_bridge_packaging():
    bridge = DesignSystemBridge()
    bundle = bridge.package_design_kit_bundle()
    assert bundle["success"] is True
    assert bundle["filename"] == "shadcn_ui_design_kit.tar.gz"
    assert bundle["files_count"] >= 50
    assert bundle["size_kb"] > 0
    assert isinstance(bundle["data"], bytes)
