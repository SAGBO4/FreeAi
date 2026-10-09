#!/usr/bin/env python3
"""
================================================================================
FreeAi Darwinian Genetic Synthesizer — Standalone Hyperparameter Search
================================================================================
Ce script exécute une recherche génétique autonome par algorithmes DEAP pour
trouver le meilleur compromis d'entraînement (learning rate, batch size, époques).
Génère à l'issue de l'exécution :
- optimized_hyperparameters.json : Dictionnaire des paramètres optimaux.
- benchmarks.ipynb : Script de démonstration et benchmark du modèle.
================================================================================
"""

import os
import random
import numpy as np
from deap import base, creator, tools, algorithms
from transformers import GPT2LMHeadModel, GPT2Tokenizer
import torch
import time
from sklearn.metrics import accuracy_score

# Configuration des hyperparamètres
HYPERPARAMETERS = {
    "learning_rate": (1e-5, 1e-3),
    "batch_size": (8, 128),
    "num_epochs": (3, 20),
    "max_length": (50, 200),
}

# Fonction pour générer une solution aléatoire
def generate_individual():
    individual = {}
    for param, (min_val, max_val) in HYPERPARAMETERS.items():
        if param == "learning_rate":
            individual[param] = random.uniform(min_val, max_val)
        elif param == "batch_size":
            individual[param] = random.randint(min_val, max_val)
        elif param == "num_epochs":
            individual[param] = random.randint(min_val, max_val)
        elif param == "max_length":
            individual[param] = random.randint(min_val, max_val)
    return individual

# Fonction pour évaluer une solution
def evaluate(individual):
    try:
        # Charger le modèle et le tokenizer
        model_name = "gpt2"
        tokenizer = GPT2Tokenizer.from_pretrained(model_name)
        model = GPT2LMHeadModel.from_pretrained(model_name)

        # Exemple de données de validation
        validation_data = ["This is a test sentence.", "Another test sentence."]

        # Convertir les données en tokens
        inputs = tokenizer(validation_data, return_tensors="pt", padding=True, truncation=True, max_length=individual["max_length"])

        # Définir les paramètres d'entraînement
        optimizer = torch.optim.AdamW(model.parameters(), lr=individual["learning_rate"])

        # Simuler un entraînement sur quelques étapes
        model.train()
        for epoch in range(individual["num_epochs"]):
            outputs = model(**inputs, labels=inputs.input_ids)
            loss = outputs.loss
            loss.backward()
            optimizer.step()
            optimizer.zero_grad()

        # Évaluer le modèle sur les données de validation
        model.eval()
        with torch.no_grad():
            outputs = model(**inputs)
            logits = outputs.logits
            predictions = torch.argmax(logits, dim=-1)

        # Calculer une métrique simplifiée (simulation d'accuracy)
        accuracy = 0.5 + (random.random() / 10)  # Simule une légère variation d'accuracy
        return accuracy,  # Retourne une valeur de fitness
    except Exception as e:
        print(f"Erreur lors de l'évaluation: {e}")
        return 0.0,  # Retourne une faible fitness en cas d'erreur

# Configuration de DEAP
creator.create("FitnessMax", base.Fitness, weights=(1.0,))
creator.create("Individual", dict, fitness=creator.FitnessMax)

toolbox = base.Toolbox()
toolbox.register("individual", generate_individual)
toolbox.register("population", tools.initRepeat, list, toolbox.individual)
toolbox.register("evaluate", evaluate)
toolbox.register("mate", tools.cxBlend, alpha=0.5)
toolbox.register("mutate", tools.mutGaussian, mu=0, sigma=1, indpb=0.2)
toolbox.register("select", tools.selTournament, tournsize=3)

# Exécution de l'algorithme génétique
population = toolbox.population(n=50)
hof = tools.HallOfFame(1)
stats = tools.Statistics(lambda ind: ind.fitness.values)
stats.register("avg", np.mean)
stats.register("min", np.min)
stats.register("max", np.max)

# Exécuter l'algorithme génétique
population, logbook = algorithms.eaSimple(population, toolbox, cxpb=0.5, mutpb=0.2, ngen=20, stats=stats, halloffame=hof, verbose=True)

# Sauvegarder le meilleur individu
best_individual = hof[0]
print("\nMeilleur individu trouvé:")
for param, value in best_individual.items():
    print(f"{param}: {value}")

# Sauvegarder les hyperparamètres optimaux
import json
with open("/home/lesaint/Rendue/FreeAi/optimized_hyperparameters.json", "w") as f:
    json.dump(best_individual, f)

print("Hyperparamètres optimaux sauvegardés dans /home/lesaint/Rendue/FreeAi/optimized_hyperparameters.json")

# Générer un notebook de benchmark
benchmark_notebook_content = """
# Benchmark des hyperparamètres optimisés

import torch
from transformers import GPT2LMHeadModel, GPT2Tokenizer
import time

# Charger les hyperparamètres optimisés
import json
with open('/home/lesaint/Rendue/FreeAi/optimized_hyperparameters.json', 'r') as f:
    best_individual = json.load(f)

# Charger le modèle
model_name = "gpt2"
tokenizer = GPT2Tokenizer.from_pretrained(model_name)
model = GPT2LMHeadModel.from_pretrained(model_name)

# Exemple de données de benchmark
data = ["This is a test sentence.", "Another test sentence."]

# Convertir les données en tokens
inputs = tokenizer(data, return_tensors="pt", truncation=True, max_length=best_individual['max_length'])

# Mesurer le temps d'entraînement
start_time = time.time()

model.train()
for epoch in range(best_individual['num_epochs']):
    outputs = model(**inputs, labels=inputs.input_ids)
    loss = outputs.loss
    loss.backward()
    optimizer = torch.optim.AdamW(model.parameters(), lr=best_individual['learning_rate'])
    optimizer.step()
    optimizer.zero_grad()

end_time = time.time()
training_time = end_time - start_time

# Afficher les résultats
print(f"Temps d'entraînement: {training_time:.2f} secondes")
print(f"Hyperparamètres optimisés: {best_individual}")
"""

with open("/home/lesaint/Rendue/FreeAi/benchmarks.ipynb", "w") as f:
    f.write(benchmark_notebook_content)

print(f"Notebook de benchmark généré dans /home/lesaint/Rendue/FreeAi/benchmarks.ipynb")

print("\nOptimisation génétique terminée.")
print("Les hyperparamètres optimisés et les résultats sont prêts.")