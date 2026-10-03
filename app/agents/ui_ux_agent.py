"""Agent UI/UX & Extreme Innovation (TDR §14 & Design Constitution).
Responsible for crafting impeccable, production-grade UIs by leveraging
exact domain templates and components from ~/Rendue/shadcn, eliminating
generic/weird machine-generated artifacts.
"""

import logging
from typing import Dict, Any, Optional, List
from .base_agent import BaseAgent
from app.tools.design_bridge import DesignSystemBridge
from app.cognition.persona import ConversationalPersona

logger = logging.getLogger("agent_ui_ux")


class UiUxAgent(BaseAgent):
    """Specialized UI/UX Architect & Extreme Innovation Engineer.
    Strictly follows the Copy & Adapt Protocol:
    1. Resolves requirement domain (Blockchain, Trading, Mobile, AI, CRM, etc.).
    2. Takes exact templates and components from ~/Rendue/shadcn.
    3. Adapts types, data structures, and branding without inventing weird UIs.
    4. Enriches with fluid animations (motion, lottie, ai-elements, tailwindcss-animate).
    """

    def __init__(
        self,
        tool_gateway,
        design_bridge: Optional[DesignSystemBridge] = None,
        persona: Optional[ConversationalPersona] = None
    ):
        super().__init__(
            name="Agent UI/UX & Extreme Innovation",
            role="Lead UI/UX Architect & Innovation Engineer",
            tool_gateway=tool_gateway
        )
        self.design_bridge = design_bridge or DesignSystemBridge()
        self.persona = persona

    async def execute_task(self, task_description: str, context: Dict[str, Any]) -> Dict[str, Any]:
        logger.info(f"[{self.name}] Executing UI/UX mission: {task_description}")

        # 1. Resolve domain
        domain = self.design_bridge.resolve_domain(task_description) or "crypto"
        template_meta = self.design_bridge.DOMAIN_TEMPLATES.get(domain, {})
        inspection = self.design_bridge.inspect_domain_template(domain)

        # 2. Check if a concrete adaptation was requested
        target_dir = context.get("target_dir")
        app_title = context.get("app_title") or f"{domain.capitalize()} Studio"

        adaptation_result = None
        if target_dir:
            adaptation_result = self.design_bridge.adapt_and_copy_template(
                domain_key=domain,
                target_dir=target_dir,
                app_title=app_title
            )

        # 3. Formulate the Innovation Touch & Guidance
        innovation_note = self._generate_innovation_touch(domain)

        return {
            "agent": self.name,
            "status": "success",
            "task": task_description,
            "domain_resolved": domain,
            "template_title": template_meta.get("title", "Modern Dashboard"),
            "source_path": inspection.get("source_path", ""),
            "domain_components": template_meta.get("components", []),
            "required_ui_primitives": inspection.get("required_ui_primitives", []),
            "animations": template_meta.get("recommended_animations", []),
            "adaptation_manifest": adaptation_result,
            "methodology": "Strict Copy & Adapt from ~/Rendue/shadcn (Zero generic AI boilerplate)",
            "innovation_touch": innovation_note
        }

    def _generate_innovation_touch(self, domain: str) -> str:
        """Adds extreme innovation, fluidity, and aesthetic guidance."""
        touches = {
            "crypto": "Intégration ticker Web3 temps réel, dark mode néon violet/émeraude, micro-interactions de swap avec Framer Motion, et sparklines Recharts sans latence.",
            "finance": "KPIs financiers dynamiques avec CountAnimation, graphiques de dépenses interactifs, badge de risque prédictif IA, et table de transactions avec filtres instantanés.",
            "ai-chat": "Sphère Lottie fluide avec pulsation synesthétique, stream Markdown instantané, barre de prompt ergonomique flottante, et tiroir de contextes rétractable.",
            "ai-image": "Galerie masonry réactive avec zoom plein écran, curseurs de diffusion fluides et Sheet responsive mobile pour l'historique de génération.",
            "mobile-tasks": "Navigation tactile pure avec Drawers Vaul ancrés en bas d'écran, swipe actions haptiques et animations de transitions page par page.",
            "crm": "Pipeline Kanban glisser-déposer (@dnd-kit), cartes de leads avec avatars dynamiques et attribution de scores prédictifs.",
            "ecommerce": "Cards produits avec hover-zoom fluide, badge de stock dynamique, panier slide-over sheet et checkout simplifié sans rechargement de page."
        }
        return touches.get(domain, "Design épuré New York, variables CSS HSL, contrastes parfaits et transitions tailwindcss-animate ultra-réactives.")
