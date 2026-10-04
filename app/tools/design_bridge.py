"""Design System & Shadcn UI Bridge for FreeAI.
Integrates local reference templates and components (~/Rendue/shadcn),
ai-elements, and fluid animations (motion, lottie, reactbeat)
with domain-specific Copy & Adapt Engine and remote export capability.
"""

import io
import os
import re
import gzip
import json
import shutil
import tarfile
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Set

logger = logging.getLogger("design_bridge")


class DesignSystemBridge:
    """Manages local shadcn/ui components catalog, pre-built domain templates,
    intelligent Copy & Adapt protocol, and remote synchronization."""

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

    DOMAIN_TEMPLATES = {
        "crypto": {
            "title": "Crypto & Blockchain Dashboard",
            "source_subpath": "app/dashboard/(auth)/crypto",
            "keywords": ["crypto", "blockchain", "web3", "wallet", "token", "dex", "defi", "bitcoin", "ethereum", "solana"],
            "components": ["overview-card", "digital-wallets", "trading-card", "recent-activities", "chart-balance-summary"],
            "recommended_animations": ["tailwindcss-animate", "motion", "count-animation"],
            "description": "Portefeuilles crypto, swap de tokens, flux de transactions blockchain, graphiques de soldes Recharts."
        },
        "finance": {
            "title": "Finance & Trading Dashboard",
            "source_subpath": "app/dashboard/(auth)/finance",
            "keywords": ["finance", "trading", "stocks", "forex", "bourse", "wallet", "expenses", "revenue", "kpi", "invest"],
            "components": ["kpi-cards", "monthly-expenses", "my-wallet", "revenue", "saving-goal", "summary", "transactions"],
            "recommended_animations": ["tailwindcss-animate", "motion", "count-animation"],
            "description": "Trading haute fréquence, gestion de portefeuille d'actifs, KPIs financiers, transactions et dépenses."
        },
        "payment": {
            "title": "Payment & Invoicing Gateway",
            "source_subpath": "app/dashboard/(auth)/payment",
            "keywords": ["payment", "paiement", "checkout", "invoices", "facture", "gateway", "stripe", "transfer"],
            "components": ["balance-overview", "exchange-rates", "notification-banner", "transaction-history"],
            "recommended_animations": ["tailwindcss-animate", "motion"],
            "description": "Passerelle de paiement, taux de change, historique de virements et alertes de facturation."
        },
        "ai-chat": {
            "title": "AI Conversational Studio & Agent Interface",
            "source_subpath": "app/dashboard/(auth)/apps/ai-chat-v2",
            "keywords": ["ai", "ia", "chat", "llm", "agent", "assistant", "jarvis", "prompt", "bot", "deepseek", "claude"],
            "components": ["ai-chat-interface", "ai-chat-sidebar", "ai-upgrade-modal"],
            "assets": ["ai-sphere-animation.json"],
            "recommended_animations": ["lottie-react", "motion", "tailwindcss-animate", "ai-elements"],
            "description": "Interface d'agent IA nouvelle génération, sphère Lottie animée, sidebar de contextes et modale d'upgrade."
        },
        "ai-image": {
            "title": "AI Visual Synthesis & Diffusion Studio",
            "source_subpath": "app/dashboard/(auth)/apps/ai-image-generator",
            "keywords": ["image", "diffusion", "midjourney", "flux", "visual", "gallery", "generator", "art"],
            "components": ["image-generator", "image-generator-form", "image-gallery", "history-sheet"],
            "recommended_animations": ["motion", "tailwindcss-animate"],
            "description": "Studio de génération d'images, panneau d'options de diffusion, historique en sheet mobile et galerie."
        },
        "ecommerce": {
            "title": "E-Commerce & Store Analytics",
            "source_subpath": "app/dashboard/(auth)/ecommerce",
            "keywords": ["ecommerce", "shop", "store", "vente", "boutique", "produits", "orders", "cart", "catalog"],
            "components": ["best-selling-products", "customer-reviews", "new-customers", "recent-orders", "return-rate", "revenue", "sales-by-location", "stat-cards", "visit-by-source"],
            "recommended_animations": ["tailwindcss-animate", "motion"],
            "description": "Ventes en ligne, commandes récentes, taux de conversion, avis clients et cartographie des ventes."
        },
        "crm": {
            "title": "CRM & Sales Pipeline",
            "source_subpath": "app/dashboard/(auth)/crm",
            "keywords": ["crm", "leads", "prospects", "pipeline", "deals", "clients", "customers", "funnel", "contacts"],
            "components": ["leads", "leads-by-source", "recent-tasks", "sales-pipeline", "target-card", "total-customers", "total-deals", "total-revenue"],
            "recommended_animations": ["tailwindcss-animate", "motion"],
            "description": "Tunnel de conversion commerciale, opportunités gagnées/perdues, attribution de leads et tâches."
        },
        "project-management": {
            "title": "Project Management & Agile Sprints",
            "source_subpath": "app/dashboard/(auth)/project-management",
            "keywords": ["project", "gestion", "jira", "linear", "sprint", "kanban", "tasks", "roadmap", "timeline", "efficiency"],
            "components": ["chart-project-efficiency", "chart-project-overview", "reminders", "reports", "success-metrics", "summary-cards", "table-recent-projects", "achievement-by-year"],
            "recommended_animations": ["dnd-kit", "tailwindcss-animate", "motion"],
            "description": "Suivi de projet agile, burndown chart, roadmap, rappels, tableau des projets récents et métriques."
        },
        "logistics": {
            "title": "Logistics & Supply Chain",
            "source_subpath": "app/dashboard/(auth)/logistics",
            "keywords": ["logistics", "logistique", "shipping", "delivery", "fleet", "warehouse", "tracking", "colis"],
            "components": [],
            "recommended_animations": ["tailwindcss-animate"],
            "description": "Suivi de flotte, expéditions en transit, gestion d'entrepôt et statuts de livraison."
        },
        "hospital": {
            "title": "Healthcare & Clinic Management",
            "source_subpath": "app/dashboard/(auth)/hospital-management",
            "keywords": ["hospital", "hopital", "health", "sante", "medical", "clinic", "doctor", "patients", "appointments"],
            "components": [],
            "recommended_animations": ["tailwindcss-animate", "motion"],
            "description": "Dossiers patients, planning médical, consultations, taux d'occupation des lits et pharmacie."
        },
        "hotel": {
            "title": "Hotel & Hospitality Bookings",
            "source_subpath": "app/dashboard/(auth)/hotel",
            "keywords": ["hotel", "hospitality", "booking", "reservation", "chambre", "resort", "tourism"],
            "components": [],
            "recommended_animations": ["tailwindcss-animate", "motion"],
            "description": "Réservations hôtelières, disponibilité des chambres, check-in/out et revenus saisonniers."
        },
        "real-estate": {
            "title": "Real Estate & Property Platform",
            "source_subpath": "app/dashboard/(auth)/real-estate",
            "keywords": ["real-estate", "immobilier", "property", "house", "apartment", "realtor", "listing", "rent"],
            "components": [],
            "recommended_animations": ["tailwindcss-animate", "motion"],
            "description": "Annonces immobilières, filtres multicritères, estimation de biens et fiches détaillées."
        },
        "analytics": {
            "title": "Website & Audience Analytics",
            "source_subpath": "app/dashboard/(auth)/website-analytics",
            "keywords": ["analytics", "traffic", "audience", "visitors", "seo", "bounce", "pageviews", "conversions"],
            "components": ["average-daily-sales", "earning-reports-card", "monthly-campaign-state", "sales-by-countries-card", "stat-cards", "tickets-card", "total-earning-card", "website-analytics-card"],
            "recommended_animations": ["tailwindcss-animate", "motion"],
            "description": "Métriques de trafic, provenance géographique, sessions actives, taux de rebond et campagnes."
        },
        "mobile-tasks": {
            "title": "Mobile App Tasks & Sheet Drawer",
            "source_subpath": "app/dashboard/(auth)/apps/tasks",
            "keywords": ["mobile", "tasks", "touch", "drawer", "sheet", "responsive", "app", "todo", "swipe"],
            "components": [],
            "recommended_animations": ["vaul", "motion", "tailwindcss-animate"],
            "description": "Expérience orientée mobile avec drawers Vaul, touch ergonomics, bottom navigation et sheets fluides."
        }
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
                target = self.shadcn_home / "components" / "ui" / clean_name
        else:
            target = self.shadcn_home / "components" / "ui" / f"{clean_name}.tsx"

        if target.exists() and target.is_file():
            return target.read_text(encoding="utf-8")
        return None

    # =========================================================================
    # DOMAIN TEMPLATES & COPY-AND-ADAPT ENGINE
    # =========================================================================

    def list_domains(self) -> List[Dict[str, Any]]:
        """Lists all supported vertical domains with their metadata."""
        domains = []
        for key, meta in self.DOMAIN_TEMPLATES.items():
            src_path = self.shadcn_home / meta["source_subpath"]
            domains.append({
                "key": key,
                "title": meta["title"],
                "description": meta["description"],
                "available": src_path.exists(),
                "path": str(src_path),
                "components": meta.get("components", []),
                "animations": meta.get("recommended_animations", []),
                "keywords": meta.get("keywords", [])
            })
        return domains

    def resolve_domain(self, query: str) -> Optional[str]:
        """Resolves a user domain prompt or keyword to a canonical domain key."""
        q = query.lower().strip()
        if q in self.DOMAIN_TEMPLATES:
            return q
        for key, meta in self.DOMAIN_TEMPLATES.items():
            if q in key or key in q:
                return key
            for kw in meta.get("keywords", []):
                if kw in q or q in kw:
                    return key
        return None

    def inspect_domain_template(self, domain_key: str) -> Dict[str, Any]:
        """Returns detailed architectural inspection of a domain template."""
        if domain_key not in self.DOMAIN_TEMPLATES:
            return {"success": False, "error": f"Domaine inconnu : {domain_key}"}

        meta = self.DOMAIN_TEMPLATES[domain_key]
        src_path = self.shadcn_home / meta["source_subpath"]
        if not src_path.exists():
            return {"success": False, "error": f"Répertoire source introuvable : {src_path}"}

        files = []
        ui_imports: Set[str] = set()

        for root, _, filenames in os.walk(src_path):
            for fname in filenames:
                fp = Path(root) / fname
                rel = fp.relative_to(src_path)
                files.append(str(rel))
                if fname.endswith((".tsx", ".ts")):
                    try:
                        content = fp.read_text(encoding="utf-8")
                        # Extract UI component imports: @/components/ui/<comp>
                        matches = re.findall(r'@/components/ui/([a-zA-Z0-9_\-]+)', content)
                        ui_imports.update(matches)
                    except Exception:
                        pass

        page_file = src_path / "page.tsx"
        page_preview = page_file.read_text(encoding="utf-8")[:1000] if page_file.exists() else ""

        return {
            "success": True,
            "domain": domain_key,
            "title": meta["title"],
            "source_path": str(src_path),
            "files": sorted(files),
            "required_ui_primitives": sorted(list(ui_imports)),
            "animations": meta.get("recommended_animations", []),
            "page_preview": page_preview
        }

    def adapt_and_copy_template(
        self,
        domain_key: str,
        target_dir: str,
        app_title: Optional[str] = None
    ) -> Dict[str, Any]:
        """Executes the Copy & Adapt Protocol:
        1. Copies the exact pre-built domain dashboard/components from ~/Rendue/shadcn.
        2. Detects all required shadcn UI primitives and copies them into target's components/ui/.
        3. Copies lib/utils.ts if missing.
        4. Customizes titles, tokens and labels.
        5. Returns a comprehensive delivery manifest.
        """
        resolved = self.resolve_domain(domain_key)
        if not resolved:
            return {"success": False, "error": f"Domaine '{domain_key}' non reconnu dans la matrice shadcn."}

        meta = self.DOMAIN_TEMPLATES[resolved]
        src_path = self.shadcn_home / meta["source_subpath"]
        if not src_path.exists():
            return {"success": False, "error": f"Répertoire source inexistant : {src_path}"}

        target_base = Path(target_dir).resolve()
        target_base.mkdir(parents=True, exist_ok=True)

        copied_domain_files = []
        copied_ui_primitives = []
        required_ui: Set[str] = set()

        # Destination paths
        dest_domain = target_base / "app" / resolved
        dest_domain.mkdir(parents=True, exist_ok=True)

        # 1. Copy domain files
        for root, _, filenames in os.walk(src_path):
            rel_root = Path(root).relative_to(src_path)
            dest_dir = dest_domain / rel_root
            dest_dir.mkdir(parents=True, exist_ok=True)
            for fname in filenames:
                src_file = Path(root) / fname
                dest_file = dest_dir / fname
                content = src_file.read_text(encoding="utf-8", errors="ignore")
                
                # Detect UI imports
                matches = re.findall(r'@/components/ui/([a-zA-Z0-9_\-]+)', content)
                required_ui.update(matches)

                # Custom adapt title if page.tsx
                if fname == "page.tsx" and app_title:
                    content = re.sub(r'title:\s*["\'].*?["\']', f'title: "{app_title}"', content)
                    content = re.sub(r'<h1[^>]*>.*?</h1>', f'<h1 className="text-xl font-bold tracking-tight lg:text-2xl">{app_title}</h1>', content)

                dest_file.write_text(content, encoding="utf-8")
                copied_domain_files.append(str(dest_file.relative_to(target_base)))

        # 2. Copy required shadcn UI primitives into components/ui
        dest_ui = target_base / "components" / "ui"
        dest_ui.mkdir(parents=True, exist_ok=True)
        src_ui = self.shadcn_home / "components" / "ui"

        for comp in required_ui:
            src_comp = src_ui / f"{comp}.tsx"
            if src_comp.exists():
                dest_comp = dest_ui / f"{comp}.tsx"
                shutil.copy2(src_comp, dest_comp)
                copied_ui_primitives.append(comp)

        # 3. Ensure lib/utils.ts exists
        dest_lib = target_base / "lib"
        dest_lib.mkdir(parents=True, exist_ok=True)
        dest_utils = dest_lib / "utils.ts"
        src_utils = self.shadcn_home / "lib" / "utils.ts"
        if not dest_utils.exists() and src_utils.exists():
            shutil.copy2(src_utils, dest_utils)

        return {
            "success": True,
            "domain": resolved,
            "app_title": app_title or meta["title"],
            "target_dir": str(target_base),
            "copied_domain_files": copied_domain_files,
            "copied_ui_primitives": copied_ui_primitives,
            "required_animations": meta.get("recommended_animations", []),
            "protocol": "Strict Copy & Adapt (Zero generic AI hallucination)"
        }

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
