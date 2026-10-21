# Architecture des Modules Réels & Pipeline Concret FreeAi

Ce document décrit l'architecture technique, les flux de données et le mode opératoire des modules réels implémentés pour remplacer les stubs et simulations dans FreeAi.

---

## 1. Cluster de Calcul Distribué de Gradients (`backend/` & `docker-compose.yml`)

### Architecture
Le système permet d'entraîner ou d'affiner des modèles d'apprentissage profond de manière distribuée sur un réseau de nœuds (workers) sans saturer une seule machine physique :

```
[ Worker 1 (Docker/GPU) ] ──┐
                            ├─► POST /gradients ──► [ Coordinator FastAPI (:8000) ]
[ Worker 2 (Docker/LAN) ] ──┘                             │ (Moyenne pondérée en RAM)
     ▲                                                    ▼
     └────── GET /gradients/update/{worker_id} ───────────┘
```

- **Coordinator (`backend/coordinator/main.py`)** :
  - Développé sous FastAPI.
  - Reçoit les tenseurs calculés via l'endpoint `/gradients`.
  - Effectue une agrégation par moyenne pondérée des gradients selon la taille du lot (`batch_size`).
  - Purge le tampon en mémoire vive dès distribution (respect du Mode NÉANT).
  - Fournit une sonde de santé `/health`.
- **Worker (`backend/worker/worker.py`)** :
  - Client PyTorch autonome.
  - Effectue la passe avant (`forward`), le calcul de perte MSE, et la rétropropagation (`loss.backward()`).
  - Gère les coupures réseau avec réessais exponentiels (`backoff factor = 2`).
  - Applique les mises à jour de poids retournées par le coordinateur.
- **Orchestration Docker (`docker-compose.yml`)** :
  - Isole le coordinateur et les workers dans un réseau virtuel pont (`bridge`).

---

## 2. Extracteur d'Intelligence Scientifique (`real_implementations/scraper.py`)

### Rôle
Alimente la mémoire vive de FreeAi en connaissances scientifiques récentes sans dépendre de listes codées en dur :

- **arXiv API (Flux Atom XML)** :
  - Endpoint officiel : `http://export.arxiv.org/api/query`.
  - Recherche ciblée sur les catégories `cs.AI`, `cs.CV`, `cs.LG`.
  - Extraction des titres, auteurs, résumés, URLs et dates de parution.
- **GitHub Search API** :
  - Extraction des dépôts open source les plus influents (`stars`, `forks`, descriptions).
  - Gestion automatique du cache d'une heure (`real_implementations/scraped_data/cache.json`) pour préserver les quotas.
  - Détection automatique de la variable `GITHUB_TOKEN` dans l'environnement.

---

## 3. Optimiseur Génétique Darwinien (`genetic_optimization.py`)

### Rôle
Découvre automatiquement les hyperparamètres idéaux pour l'entraînement d'un modèle de langage (GPT-2) en fonction du matériel disponible :

- **Algorithme d'Évolution (Framework DEAP)** :
  - **Espace des gènes** : `learning_rate` [1e-5, 1e-3], `batch_size` [8, 32], `num_epochs` [3, 8], `max_length` [30, 80].
  - **Population** : 15 individus par génération.
  - **Sélection** : Tournoi de taille 3.
  - **Croisement (Crossover)** : `cxBlend` (alpha=0.5).
  - **Mutation** : Gaussienne (sigma=0.2, indpb=0.2).
  - **Hall of Fame** : Sauvegarde continue du meilleur champion absolu.
- **Livrables produits** :
  - `optimized_hyperparameters.json` : Fichier structuré exploitable directement par les pipelines d'entraînement.
  - `benchmark_report.txt` : Historique des métriques de convergence.
