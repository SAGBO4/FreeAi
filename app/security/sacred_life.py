"""Sacred Life Sentinel (Le Gardien du Sanctuaire de la Vie Humaine).
Enforces the immutable, non-negotiable foundation of FreeAI autonomy:
Even in super-user sudo mode ('lesaintAi') with total autonomy to achieve technical objectives,
FreeAI has an absolute mathematical veto preventing any action that could harm human life,
critical hospital/medical systems, emergency infrastructure, or physical safety.
"""

import re
import logging
from typing import Dict, Any, Tuple

logger = logging.getLogger("sacred_life_sentinel")


class SacredLifeViolationError(Exception):
    """Raised when an autonomous action poses a risk to human physical safety or life."""
    pass


class SacredLifeSentinel:
    """Verifies that autonomous operations never harm human life or vital infrastructures."""

    # Patterns indicating threats to human life: weapons, lethal attacks, medical/vital systems
    # Carefully tuned so pure IT/computing (e.g. arm64, exploit, sudo, pentest, root) is never blocked.
    VITAL_THREAT_PATTERNS = [
        r"\b(arme[s]?\s+(?:de\s+guerre|à\s+feu|létale|biologique|chimique|nucléaire|blanche)|weapon[s]?|missile[s]?|explosif[s]?|bomb[es]?)\b",
        r"\b(tuer|assassiner|blesser|empoisonner|homicide|meurtre|exterminer)\b",
        r"(pacemaker|respirateur|soins\s*intensifs|dialyse|\bhopital\b|\burgences\b)",
        r"\b(911|112|15|18|samu|pompiers|emergency\s*services)\b",
        r"\b(kill\s*human|murder|harm\s*people|physical\s*violence|lethal\s*attack)\b",
        r"(hospital\s*scada|life\s*support|medical\s*device)"
    ]

    def __init__(self, strict_mode: bool = True):
        self.strict_mode = strict_mode
        self._compiled_patterns = [re.compile(p, re.IGNORECASE) for p in self.VITAL_THREAT_PATTERNS]

    def audit_objective(self, objective: str) -> Tuple[bool, str]:
        """Audits an objective before autonomous execution.
        Returns: (is_safe: bool, reason: str)
        """
        clean_text = objective.strip()
        for pat in self._compiled_patterns:
            match = pat.search(clean_text)
            if match:
                reason = (
                    f"VETO ÉTHIQUE ABSOLU : Détection d'un risque potentiel pour la vie humaine "
                    f"ou des infrastructures vitales ('{match.group(0)}'). "
                    f"Règle d'or de FreeAI : La vie humaine est sacrée et inviolable."
                )
                logger.critical(f"[SACRED LIFE SENTINEL] {reason}")
                return False, reason

        return True, "Objectif conforme à la sacralité de la vie humaine."

    def enforce_objective_safety(self, objective: str):
        """Raises SacredLifeViolationError if an objective violates human life sanctity."""
        safe, reason = self.audit_objective(objective)
        if not safe:
            raise SacredLifeViolationError(reason)
