"""Design System & Shadcn UI Bridge for FreeAI.
Integrates local reference components (~/Rendue/shadcn) and ai-elements
with remote export capability to Telegram Neural Vault and Neon Cloud.
"""

import io
import os
import gzip
import json
import tarfile
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger("design_bridge")


class DesignSystemBridge:
    """Manages local shadcn/ui components catalog, design tokens,
    and remote synchronisation to Telegram and Neon."""

    DEFAULT_SHADCN_HOME = Path("/home/lesaint/Rendue/shadcn")

    CATEGORIES = {
        "layout": ["card", "separator", "aspect-ratio", "resizable", "scroll-area", "sidebar"],
        "inputs": [
            "button", "button-group", "input", "input-group", "input-otp", "textarea",
            "checkbox", "radio-group", "select", "native-select", "switch", "slider",
            "form", "label", "field", "combobox"
        ],
        "overlay": [
            "dialog", "alert-dialog", "drawer", "sheet", "popover", "hover-card",
            "tooltip", "context-menu", "dropdown-menu", "menubar", "navigation-menu"
        ],
        "feedback": ["alert", "badge", "progress", "skeleton", "spinner", "sonner", "toast"],
        "data_display": [
            "table", "chart", "avatar", "calendar", "carousel", "reel", "kanban",
            "pagination", "breadcrumb", "tabs", "accordion", "collapsible", "command",
            "timeline", "item", "empty", "kbd"
        ],
        "custom": ["count-animation", "prompt", "tiptap"]
    }

    def __init__(self, shadcn_home: Optional[str] = None):
        self.shadcn_home = Path(shadcn_home or self.DEFAULT_SHADCN_HOME).resolve()

    @property
    def is_available(self) -> bool:
        return (self.shadcn_home / "components" / "ui").exists()

    def list_components(self) -> List[str]:
        """Lists all component names available in the local repository."""
        ui_dir = self.shadcn_home / "components" / "ui"
        if not ui_dir.exists():
            return []
        comps = []
        for f in ui_dir.glob("*.tsx"):
            comps.append(f.stem)
        custom_dir = ui_dir / "custom"
        if custom_dir.exists():
            for item in custom_dir.iterdir():
                if item.is_dir() or item.suffix in (".tsx", ".ts"):
                    comps.append(f"custom/{item.stem}")
        return sorted(comps)

    def get_catalog_by_categories(self) -> Dict[str, List[str]]:
        """Returns components grouped by functional category."""
        all_comps = set(self.list_components())
        catalog = {}
        for cat, comps in self.CATEGORIES.items():
            found = [c for c in comps if c in all_comps or f"custom/{c}" in all_comps]
            catalog[cat] = found
        # Any remaining components
        categorized = {c for comps in catalog.values() for c in comps}
        others = [c for c in all_comps if c not in categorized and not c.startswith("custom/")]
        if others:
            catalog["other"] = others
        return catalog

    def search_components(self, query: str) -> List[str]:
        """Searches components by name substring."""
        q = query.lower().strip()
        return [c for c in self.list_components() if q in c.lower()]

    def read_component_code(self, component_name: str) -> Optional[str]:
        """Reads TypeScript source code for a specific component."""
        clean_name = component_name.strip()
        if clean_name.startswith("custom/"):
            target = self.shadcn_home / "components" / "ui" / f"{clean_name}.tsx"
            if not target.exists():
                # Directory check
                target = self.shadcn_home / "components" / "ui" / clean_name
        else:
            target = self.shadcn_home / "components" / "ui" / f"{clean_name}.tsx"

        if target.exists() and target.is_file():
            return target.read_text(encoding="utf-8")
        return None

    def package_design_kit_bundle(self) -> Dict[str, Any]:
        """Packages components/ui, hooks, lib/utils and components.json into an
        in-memory GZIP compressed tarball. Zero local disk write (Mode NÉANT)."""
        if not self.is_available:
            return {"success": False, "error": "Dépôt local shadcn non trouvé."}

        buffer = io.BytesIO()
        packaged_count = 0

        with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
            # 1. components/ui
            ui_dir = self.shadcn_home / "components" / "ui"
            if ui_dir.exists():
                for root, dirs, files in os.walk(ui_dir):
                    for file in files:
                        p = Path(root) / file
                        arcname = str(Path("components/ui") / p.relative_to(ui_dir))
                        tar.add(str(p), arcname=arcname)
                        packaged_count += 1

            # 2. hooks
            hooks_dir = self.shadcn_home / "hooks"
            if hooks_dir.exists():
                for f in hooks_dir.glob("*.ts*"):
                    tar.add(str(f), arcname=f"hooks/{f.name}")
                    packaged_count += 1

            # 3. lib/utils.ts
            lib_utils = self.shadcn_home / "lib" / "utils.ts"
            if lib_utils.exists():
                tar.add(str(lib_utils), arcname="lib/utils.ts")
                packaged_count += 1

            # 4. components.json
            comp_json = self.shadcn_home / "components.json"
            if comp_json.exists():
                tar.add(str(comp_json), arcname="components.json")
                packaged_count += 1

        buffer.seek(0)
        bundle_bytes = buffer.getvalue()
        size_kb = len(bundle_bytes) / 1024.0

        return {
            "success": True,
            "filename": "shadcn_ui_design_kit.tar.gz",
            "files_count": packaged_count,
            "size_kb": size_kb,
            "data": bundle_bytes
        }

    async def export_to_telegram(self, telegram_vault: Any) -> Dict[str, Any]:
        """Teleports the entire Shadcn UI design kit to Telegram Cloud storage."""
        bundle = self.package_design_kit_bundle()
        if not bundle.get("success"):
            return bundle

        caption = (
            f"🎨 <b>[Kit Design Shadcn/UI & AI Elements]</b>\n"
            f"• Composants packagés : {bundle['files_count']} fichiers\n"
            f"• Poids compressé GZIP : {bundle['size_kb']:.2f} Ko\n"
            f"• Source locale : <code>~/Rendue/shadcn</code>\n"
            f"• Mode NÉANT : 0 octet écrit sur disque"
        )
        ok = await telegram_vault.send_document(
            bundle["filename"],
            bundle["data"],
            caption=caption
        )
        bundle["uploaded_to_telegram"] = ok
        del bundle["data"]
        return bundle
