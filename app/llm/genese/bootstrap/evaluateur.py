import math
import re

class EvaluateurConsensus:
    """
    Evaluateur de qualité des réponses.
    Compare la réponse de deux modèles professeurs par similarité sémantique
    sur des embeddings simples (TF-IDF basique) ou similarité lexicale.
    """
    
    def _get_words(self, text: str) -> dict:
        words = re.findall(r'\w+', text.lower())
        freq = {}
        for w in words:
            if len(w) > 2:
                freq[w] = freq.get(w, 0) + 1
        return freq

    def calculer_consensus(self, rep1: str, rep2: str) -> float:
        """
        Score de consensus entre 0.0 et 1.0.
        Utilise une similarité cosinus sur les fréquences de mots.
        """
        if not rep1 or not rep2:
            return 0.0
            
        freq1 = self._get_words(rep1)
        freq2 = self._get_words(rep2)
        
        mots_communs = set(freq1.keys()) & set(freq2.keys())
        dot_product = sum(freq1[w] * freq2[w] for w in mots_communs)
        
        norm1 = math.sqrt(sum(v*v for v in freq1.values()))
        norm2 = math.sqrt(sum(v*v for v in freq2.values()))
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
            
        score = dot_product / (norm1 * norm2)
        
        # Détection basique de contradictions
        contradictions = ["non", "faux", "erreur", "impossible"]
        c1 = sum(1 for c in contradictions if c in freq1)
        c2 = sum(1 for c in contradictions if c in freq2)
        if c1 != c2: # L'un contredit l'autre
            score *= 0.8
            
        return score
