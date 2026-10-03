from typing import Tuple
from .constitution import PRINCIPES

class GardienEthique:
    """
    Gardien éthique du modèle Jarvis.
    Non-entraînable (gelé). Il évalue les probabilités ou le texte généré
    en complément du SacredLifeSentinel existant.
    """
    def __init__(self):
        self.principes = PRINCIPES

    def evaluer_generation(self, texte: str) -> Tuple[bool, str]:
        """
        Vérifie si le texte généré viole les principes constitutionnels de base.
        Retourne (Est_Valide, Raison_Si_Invalide).
        """
        texte_lower = texte.lower()
        mots_interdits = ["tuer", "assassiner", "détruire", "suicide", "génocide"]
        
        for mot in mots_interdits:
            if mot in texte_lower:
                return False, f"Violation constitutionnelle: référence à '{mot}'"
                
        return True, ""

    def filtrer(self, texte: str) -> str:
        valide, raison = self.evaluer_generation(texte)
        if not valide:
            return "[CENSURÉ PAR LE GARDIEN JARVIS: Le contenu généré a violé les principes constitutionnels.]"
        return texte
