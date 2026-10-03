import dataclasses
import random

@dataclasses.dataclass
class Genome:
    """
    Hyperparamètres d'apprentissage soumis à l'évolution darwinienne.
    """
    learning_rate: float = 3e-4
    melange: float = 0.5            # Ratio d'exploration du batch
    temperature_curiosite: float = 1.0 # Temperature pour les rêves
    force_ancrage: float = 0.5      # Force de l'EWC
    lr_anciens_experts: float = 1e-5 # Pour le stade MoE
    
    def muter(self, taux_mutation: float = 0.1) -> 'Genome':
        """Génère un nouveau génome muté."""
        def muter_val(val, variance=0.2):
            if random.random() < taux_mutation:
                return val * random.uniform(1.0 - variance, 1.0 + variance)
            return val
            
        return Genome(
            learning_rate=muter_val(self.learning_rate),
            melange=max(0.1, min(0.9, muter_val(self.melange))),
            temperature_curiosite=max(0.5, min(2.0, muter_val(self.temperature_curiosite))),
            force_ancrage=max(0.1, min(5.0, muter_val(self.force_ancrage))),
            lr_anciens_experts=muter_val(self.lr_anciens_experts)
        )
