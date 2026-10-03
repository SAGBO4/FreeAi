import math
from typing import List, Tuple

class SouvenirsEpisodiques:
    """
    Index vectoriel en RAM pour la mémoire épisodique à court/moyen terme.
    Utilise une similarité cosinus basique si FAISS n'est pas disponible pour garder
    le système léger (zéro dépendance externe lourde stricte).
    """
    def __init__(self, dimension: int = 384):
        self.dimension = dimension
        self.vecteurs = [] # List of tuples (id, list of floats)
        self.textes = {} # id -> str
        self.next_id = 0

    def ajouter_souvenir(self, texte: str, vecteur: List[float]):
        if len(vecteur) != self.dimension:
            raise ValueError(f"La dimension du vecteur doit être {self.dimension}")
        self.vecteurs.append((self.next_id, vecteur))
        self.textes[self.next_id] = texte
        self.next_id += 1

    def _cosine_similarity(self, v1: List[float], v2: List[float]) -> float:
        dot_product = sum(a * b for a, b in zip(v1, v2))
        norm1 = math.sqrt(sum(a * a for a in v1))
        norm2 = math.sqrt(sum(a * a for a in v2))
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot_product / (norm1 * norm2)

    def rechercher(self, vecteur_requete: List[float], k: int = 5) -> List[Tuple[str, float]]:
        scores = []
        for vid, v in self.vecteurs:
            score = self._cosine_similarity(vecteur_requete, v)
            scores.append((score, vid))
        
        scores.sort(reverse=True, key=lambda x: x[0])
        resultats = []
        for score, vid in scores[:k]:
            resultats.append((self.textes[vid], score))
            
        return resultats
