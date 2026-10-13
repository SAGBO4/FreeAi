#!/usr/bin/env python3

"""
Script de benchmark pour mesurer les performances du calcul de gradients.
"""

import time
import torch
import torch.nn as nn
from worker.worker import compute_gradients

# Modèle PyTorch simple pour le benchmark
def benchmark_compute_gradients(batch_size: int, iterations: int = 10):
    """Mesure le temps de calcul des gradients pour une taille de batch donnée."""
    model = nn.Linear(10, 3)

    total_time = 0.0
    for _ in range(iterations):
        start_time = time.time()

        # Générer des données aléatoires
        x = torch.randn(batch_size, 10)
        y = torch.randn(batch_size, 3)

        # Calculer les gradients
        output = model(x)
        loss = nn.MSELoss()(output, y)
        loss.backward()

        # Récupérer les gradients
        gradients = {}
        for name, param in model.named_parameters():
            if param.grad is not None:
                gradients[name] = param.grad.data.mean().item()

        end_time = time.time()
        total_time += end_time - start_time

    avg_time = total_time / iterations
    return avg_time

if __name__ == "__main__":
    batch_sizes = [32, 64, 128, 256]

    print("Benchmark des performances de calcul de gradients:")
    print("--------------------------------------------------")

    for batch_size in batch_sizes:
        avg_time = benchmark_compute_gradients(batch_size)
        print(f"Taille de batch: {batch_size} | Temps moyen: {avg_time:.4f} secondes")