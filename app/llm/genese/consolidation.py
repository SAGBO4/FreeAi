import random
from typing import List, Dict

class ConsolidationNocturne:
    """
    Gère la préparation des données pour l'entraînement non supervisé nocturne.
    Mélange le ratio demandé: 45% nouveau, 25% souvenirs, 10% rêves, 20% fondation.
    """
    def __init__(self, index_memoire):
        self.index = index_memoire

    def preparer_batch(self, taille_batch: int = 32) -> List[str]:
        """
        Génère un batch de textes respectant la distribution catadienne.
        """
        repartition = {
            "nouveau": int(taille_batch * 0.45),
            "souvenirs": int(taille_batch * 0.25),
            "reves": int(taille_batch * 0.10),
            "fondation": taille_batch - int(taille_batch * 0.45) - int(taille_batch * 0.25) - int(taille_batch * 0.10)
        }
        
        batch = []
        for categorie, nb in repartition.items():
            shards = self.index.obtenir_shards(categorie, limite=100)
            if shards:
                batch.extend(random.choices(shards, k=nb))
            else:
                # Fallback générique si manque de données
                batch.extend(["<|jarvis|> Le modèle explore le néant pour trouver du sens."] * nb)
                
        random.shuffle(batch)
        return batch
