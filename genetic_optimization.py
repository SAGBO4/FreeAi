#!/usr/bin/env python3
"""
================================================================================
FreeAi Sovereign Genetic Hyperparameter Optimizer (Algorithmes Génétiques DEAP)
================================================================================
Ce module applique la sélection naturelle darwinienne pour découvrir automatiquement
la meilleure combinaison d'hyperparamètres d'entraînement pour un modèle de langage (GPT-2) :
1. Espace de recherche :
   - learning_rate : [1e-5, 1e-3] (taux d'apprentissage continu)
   - batch_size : {8, 16, 24, 32} (taille de lot adaptée à la RAM/VRAM)
   - num_epochs : [3, 8] (nombre d'itérations d'entraînement)
   - max_length : [30, 80] (longueur de séquence de contexte)
2. Moteur évolutionnaire (DEAP) :
   - Population : 15 individus par génération
   - Sélection : Tournoi (taille 3)
   - Croisement : Blending (cxBlend avec alpha=0.5)
   - Mutation : Gaussienne (sigma=0.2, probabilité=0.2)
   - Hall of Fame : Conservation du meilleur champion absolu
================================================================================
"""

import os
import random
import time
import json
import logging
import numpy as np
import torch
from deap import base, creator, tools, algorithms
from transformers import GPT2LMHeadModel, GPT2Tokenizer

# Configuration du logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("freeai.genetic_optimizer")

# 1. Détection dynamique du matériel accélérateur
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
logger.info(f"Dispositif de calcul détecté pour l'optimisation : {device}")

# 2. Définition des bornes d'hyperparamètres (frugales et adaptées)
HYPERPARAMETERS = {
    "learning_rate": (1e-5, 1e-3),
    "batch_size": (8, 32),
    "num_epochs": (3, 8),
    "max_length": (30, 80)
}

# 3. Répertoire de sortie (supporte l'exécution dans Docker /app ou en local)
OUTPUT_DIR = "/app" if os.path.exists("/app") and os.access("/app", os.W_OK) else "."


def generate_individual() -> dict:
    """
    Génère un individu aléatoire (chromosome) dans l'espace des hyperparamètres.
    Chaque individu est un dictionnaire associant un nom de paramètre à sa valeur.
    """
    individual = {}
    for param, (min_val, max_val) in HYPERPARAMETERS.items():
        if param == "learning_rate":
            individual[param] = random.uniform(min_val, max_val)
        elif param == "batch_size":
            # Tailles de lots alignées sur un multiple de 8 pour les performances GPU/CPU
            individual[param] = random.choice([x for x in range(min_val, max_val + 1) if x % 8 == 0])
        elif param == "num_epochs":
            individual[param] = random.randint(min_val, max_val)
        elif param == "max_length":
            individual[param] = random.randint(min_val, max_val)
    return individual


def evaluate(individual: dict) -> tuple:
    """
    Fonction de fitness : évalue la performance d'un jeu d'hyperparamètres.
    Simule une passe d'entraînement rapide sur un mini-batch et retourne le score d'aptitude.
    """
    try:
        model_name = "gpt2"
        tokenizer = GPT2Tokenizer.from_pretrained(model_name)
        model = GPT2LMHeadModel.from_pretrained(model_name).to(device)

        # Jeu de validation minimal pour l'évaluation de fitness
        validation_data = ["FreeAi is a sovereign artificial intelligence.", "Autonomous coding in zero disk mode."]

        # Tokenisation avec troncature selon la longueur du chromosome
        inputs = tokenizer(
            validation_data,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=individual["max_length"]
        ).to(device)

        # Optimiseur AdamW avec le learning rate sélectionné
        optimizer = torch.optim.AdamW(model.parameters(), lr=individual["learning_rate"])

        # Micro-entraînement pour mesurer la convergence
        model.train()
        for _ in range(min(individual["num_epochs"], 2)):
            outputs = model(**inputs, labels=inputs.input_ids)
            loss = outputs.loss
            loss.backward()
            optimizer.step()
            optimizer.zero_grad()

        # Évaluation en mode inférence
        model.eval()
        with torch.no_grad():
            outputs = model(**inputs)
            # Fitness inverse de la perte pour maximisation
            loss_val = float(outputs.loss.item()) if hasattr(outputs, "loss") and outputs.loss is not None else 1.0

        # Score de fitness (plus la perte est basse, plus la fitness est haute)
        fitness_score = 1.0 / (1.0 + max(0.01, loss_val))
        return fitness_score,

    except Exception as e:
        logger.warning(f"Erreur lors de l'évaluation de l'individu: {e}")
        # En cas d'erreur mémoire ou OOM, pénaliser l'individu
        return 0.0,


# ==============================================================================
# 4. Configuration du Framework DEAP
# ==============================================================================
# Objectif : maximiser la fitness (+1.0)
if not hasattr(creator, "FitnessMax"):
    creator.create("FitnessMax", base.Fitness, weights=(1.0,))
if not hasattr(creator, "Individual"):
    creator.create("Individual", dict, fitness=creator.FitnessMax)

toolbox = base.Toolbox()
toolbox.register("individual", generate_individual)
toolbox.register("population", tools.initRepeat, list, toolbox.individual)
toolbox.register("evaluate", evaluate)
toolbox.register("mate", tools.cxBlend, alpha=0.5)
toolbox.register("mutate", tools.mutGaussian, mu=0, sigma=0.2, indpb=0.2)
toolbox.register("select", tools.selTournament, tournsize=3)


def run_evolution():
    """Exécute l'algorithme génétique complet et sauvegarde les artefacts."""
    logger.info("Initialisation de la population darwinienne (15 individus)...")
    population = toolbox.population(n=15)
    hof = tools.HallOfFame(1)

    stats = tools.Statistics(lambda ind: ind.fitness.values)
    stats.register("avg", np.mean)
    stats.register("min", np.min)
    stats.register("max", np.max)

    logger.info("Lancement de l'évolution sur 10 générations...")
    population, logbook = algorithms.eaSimple(
        population,
        toolbox,
        cxpb=0.5,
        mutpb=0.2,
        ngen=10,
        stats=stats,
        halloffame=hof,
        verbose=True
    )

    # 5. Extraction et persistance du champion
    best_individual = hof[0]
    print("\n" + "=" * 60)
    print("🏆 MEILLEUR JEU D'HYPERPARAMÈTRES DÉCOUVERT :")
    print("=" * 60)
    for param, value in best_individual.items():
        print(f"  • {param:15s} : {value}")

    # Sauvegarde JSON
    target_json = os.path.join(OUTPUT_DIR, "optimized_hyperparameters.json")
    with open(target_json, "w", encoding="utf-8") as f:
        json.dump(best_individual, f, indent=2)
    logger.info(f"Hyperparamètres optimaux enregistrés dans {target_json}")

    # Rapport d'analyse textuel
    benchmark_report = f"""# Rapport de Benchmark — Optimisation Génétique FreeAi

Date d'exécution : {time.strftime('%Y-%m-%d %H:%M:%S')}
Dispositif physique : {device}
Taille de population : 15
Nombre de générations : 10

Hyperparamètres Optimaux Gagnants :
{json.dumps(best_individual, indent=4)}
"""
    target_report = os.path.join(OUTPUT_DIR, "benchmark_report.txt")
    with open(target_report, "w", encoding="utf-8") as f:
        f.write(benchmark_report)
    logger.info(f"Rapport de benchmark généré dans {target_report}")


if __name__ == "__main__":
    run_evolution()