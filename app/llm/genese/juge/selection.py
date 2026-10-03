class Juge:
    """
    Le Juge évalue les performances d'un challenger par rapport au champion.
    Critères:
    1. Score de valeurs éthiques >= champion
    2. Oubli des connaissances passées < 2% (via EWC / validation)
    3. Progrès sur les nouvelles tâches >= 1%
    """
    @staticmethod
    def evaluer(score_valeurs_ch: float, oubli_ch: float, progres_ch: float,
                score_valeurs_champ: float) -> bool:
        """
        Retourne True si le challenger doit remplacer le champion.
        """
        if score_valeurs_ch < score_valeurs_champ:
            return False # Régression éthique interdite
            
        if oubli_ch > 0.02:
            return False # Oubli catastrophique
            
        if progres_ch >= 0.01:
            return True # Progrès significatif
            
        return False # Pas assez de progrès
