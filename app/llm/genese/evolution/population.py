from typing import List
from .genome import Genome

class GestionPopulation:
    """
    Gère la population de challengers pendant une phase d'évolution.
    """
    def __init__(self, taille_population: int = 4):
        self.taille_population = taille_population

    def generer_challengers(self, champion_genome: Genome) -> List[Genome]:
        """
        Génère N-1 challengers mutés à partir du champion.
        Le champion lui-même est inclus dans l'évaluation.
        """
        population = [champion_genome]
        for _ in range(self.taille_population - 1):
            population.append(champion_genome.muter())
        return population
