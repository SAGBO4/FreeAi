class CurriculumAdaptatif:
    """
    Détermine l'ordre et la fréquence des catégories de benchmark
    selon le progrès d'apprentissage du noyau JARVIS.
    """
    def __init__(self):
        self.historique_pertes = {} # categorie -> [pertes]
        self.priorites = {}

    def ajouter_perte(self, categorie: str, perte: float):
        if categorie not in self.historique_pertes:
            self.historique_pertes[categorie] = []
        self.historique_pertes[categorie].append(perte)
        # Limiter historique
        if len(self.historique_pertes[categorie]) > 10:
            self.historique_pertes[categorie] = self.historique_pertes[categorie][-10:]

    def calculer_priorites(self) -> dict:
        """
        - Zone déjà maîtrisée (perte basse, stable) → baisser la priorité
        - Zone de progrès rapide (perte baisse vite) → MAXIMISER
        - Zone de chaos (perte haute, aucun progrès) → mettre en attente
        """
        from .distillateur import CATEGORIES_BENCHMARK
        for cat in CATEGORIES_BENCHMARK.keys():
            pertes = self.historique_pertes.get(cat, [])
            if len(pertes) < 2:
                self.priorites[cat] = 1.0 # Priorité par défaut
                continue
                
            derniere = pertes[-1]
            avant_derniere = pertes[-2]
            delta = avant_derniere - derniere
            
            if derniere < 0.5: # Maîtrisé
                self.priorites[cat] = max(0.1, self.priorites.get(cat, 1.0) - 0.1)
            elif delta > 0.05: # Progrès rapide (>5%)
                self.priorites[cat] = min(2.0, self.priorites.get(cat, 1.0) + 0.2)
            elif delta < 0 and derniere > 2.0: # Chaos (perte augmente et reste haute)
                self.priorites[cat] = max(0.2, self.priorites.get(cat, 1.0) - 0.2)

        return self.priorites

    async def prochaine_session(self) -> str:
        """Retourne la catégorie avec la plus haute priorité."""
        self.calculer_priorites()
        if not self.priorites:
            from .distillateur import CATEGORIES_BENCHMARK
            return list(CATEGORIES_BENCHMARK.keys())[0]
            
        return max(self.priorites.items(), key=lambda x: x[1])[0]
