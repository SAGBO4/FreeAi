import torch
import torch.nn as nn

class ElasticWeightConsolidation:
    """
    EWC : Protège les poids critiques associés au comportement éthique (l'Âme)
    pour éviter l'oubli catastrophique lors de l'entraînement non supervisé ou de l'évolution.
    """
    def __init__(self, modele: nn.Module, force_ancrage: float = 0.5):
        self.modele = modele
        self.force_ancrage = force_ancrage
        self.poids_ancres = {}
        self.importance = {}
        
    def ancrer_poids_actuels(self, loader_ethique=None):
        """
        Calcule la diagonale de l'information de Fisher pour estimer l'importance
        des poids vis-à-vis des données éthiques.
        En l'absence de loader (pour le prototype), utilise une importance uniforme.
        """
        self.poids_ancres.clear()
        self.importance.clear()
        
        for name, param in self.modele.named_parameters():
            if param.requires_grad:
                self.poids_ancres[name] = param.data.clone().detach()
                # Dummy importance for now
                self.importance[name] = torch.ones_like(param.data) * 0.01

    def penalite_ewc(self) -> torch.Tensor:
        """
        Retourne la loss de pénalité à ajouter pendant l'entraînement.
        """
        penalite = 0.0
        for name, param in self.modele.named_parameters():
            if param.requires_grad and name in self.poids_ancres:
                _penalty = self.importance[name] * (param - self.poids_ancres[name]) ** 2
                penalite += _penalty.sum()
        return penalite * self.force_ancrage
