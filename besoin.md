# 📋 Guide & Cahier des Besoins Personnels — Actions Requises (Utilisateur)

Ce document détaille **exclusivement les actions que vous (l'utilisateur) devez accomplir personnellement** sur votre machine Kali Linux pour finaliser, exécuter et valider les implémentations réelles de **FreeAi**.

---

## 🎯 Synthèse des Modules Réels Disponibles

| Module | Fichiers Clés | Ce qu'il fait | Niveau d'Action |
|---|---|---|---|
| **1. Optimisation Génétique** | `genetic_optimization.py`, `run_genetic_optimization.sh` | Optimise par algorithme génétique (DEAP) les hyperparamètres (LR, batch size, epochs, context length). | 🟢 Commande à exécuter |
| **2. Scraper d'Intelligence (arXiv / GitHub)** | `real_implementations/scraper.py` | Récupère les derniers papiers IA (arXiv) et dépôts GitHub tendance sans simulation. | 🟡 Token GitHub + Exécution |
| **3. Calcul Distribué de Gradients** | `docker-compose.yml`, `backend/` | Cluster Coordinator + Workers isolés dans Docker pour l'agrégation de gradients. | 🟢 Lancement Docker |

---

## ⚙️ Étape 1 : Pré-requis Système & Permissions Docker

Docker est nécessaire pour isoler le cluster et exécuter l'optimisation génétique sans polluer votre système Kali.

Exécutez dans votre terminal :
```bash
# 1. Vérifier / démarrer le service Docker
sudo systemctl enable --now docker

# 2. Donner les permissions Docker à votre utilisateur (évite d'avoir à faire sudo docker)
sudo usermod -aG docker $USER

# 3. Appliquer immédiatement les permissions au terminal courant
newgrp docker
```
> **Vérification** : Lancez `docker ps`. Si la commande s'exécute sans erreur de permission, Docker est prêt.

---

## 🔑 Étape 2 : Configuration du Token GitHub (Indispensable pour le Scraper)

Par défaut, l'API publique de GitHub bloque les requêtes non authentifiées après 60 appels par heure. Pour alimenter le scraper et le radar de bounties en continu (5 000 requêtes/heure) :

1. Ouvrez votre navigateur sur [GitHub Developer Settings - Tokens](https://github.com/settings/tokens).
2. Cliquez sur **Generate new token (classic)**.
3. Donnez-lui un nom (ex: `FreeAi-Scraper`) et cochez :
   - `repo` (accès complet aux dépôts)
   - `read:org` (lecture des organisations)
4. Copiez le token généré (`ghp_...`).
5. Ajoutez-le dans votre fichier `.env` à la racine de `FreeAi` :
```bash
echo "GITHUB_TOKEN=ghp_VOTRE_TOKEN_ICI" >> .env
```
*(Le script `real_implementations/scraper.py` lira automatiquement cette variable d'environnement).*

---

## 🚀 Étape 3 : Exécution des Nouveaux Modules

### Option A. Module d'Optimisation Génétique des Hyperparamètres

Ce module utilise l'algorithme génétique `eaSimple` de DEAP pour tester différentes combinaisons d'hyperparamètres et identifier la configuration optimale.

#### Méthode 1 : Via Docker (Recommandée — 0 installation locale)
```bash
cd /home/lesaint/Rendue/FreeAi

# Rendre le script exécutable
chmod +x run_genetic_optimization.sh

# Lancer l'optimisation dans le conteneur worker1
./run_genetic_optimization.sh
```

#### Méthode 2 : Directement en Python local (CPU ou GPU)
Si vous préférez tester rapidement dans un environnement virtuel dédié :
```bash
# 1. Créer et activer l'environnement temporaire
python3 -m venv /tmp/genetic_venv
source /tmp/genetic_venv/bin/activate

# 2. Installer les dépendances CPU
pip install --upgrade pip
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
pip install deap transformers numpy scikit-learn

# 3. Lancer l'algorithme génétique
python3 genetic_optimization.py
```

> **Résultats générés à vérifier :**
> - `optimized_hyperparameters.json` : Contient le meilleur taux d'apprentissage, batch size et nombre d'époques.
> - `benchmark_report.txt` : Rapport détaillé d'évolution sur les 10 générations.

---

### Option B. Module de Veille d'Intelligence (arXiv & GitHub Scraper)

Ce script interroge le flux réel Atom d'arXiv (`export.arxiv.org`) et l'API GitHub pour extraire les avancées IA en temps réel.

```bash
# Exécution du scraper
python3 real_implementations/scraper.py
```

> **Résultats générés à vérifier dans `real_implementations/scraped_data/` :**
> - `arxiv_data.json` : Résumés et métadonnées des derniers articles scientifiques IA.
> - `github_data.json` : Dépôts IA tendances, étoiles, forks et descriptions.

---

### Option C. Lancement du Cluster Distribué (Coordinator + Workers)

Le système de gradients distribué permet d'exécuter un coordinateur FastAPI et plusieurs nœuds d'entraînement connectés en réseau.

```bash
cd /home/lesaint/Rendue/FreeAi

# 1. Construire et démarrer le cluster en arrière-plan
docker-compose up --build -d

# 2. Suivre les logs en temps réel pour observer les échanges de gradients
docker-compose logs -f

# 3. Tester la santé du Coordinator depuis votre terminal :
curl http://127.0.0.1:8000/health

# 4. Arrêter le cluster proprement quand vous avez terminé :
docker-compose down
```

---

## 🛠️ Résolution des Problèmes Courants (Dépannage)

| Symptôme | Cause Réelle | Solution Immédiate |
|---|---|---|
| `Got permission denied while trying to connect to the Docker daemon` | Utilisateur non inclus dans le groupe `docker`. | Lancez `sudo usermod -aG docker $USER` puis `newgrp docker`. |
| `API rate limit exceeded for ... (GitHub)` | Requêtes anonymes limitées à 60/h. | Définissez votre token : `export GITHUB_TOKEN=ghp_...`. |
| `Host api.arxiv.org not found (NXDOMAIN)` | Le domaine `api.arxiv.org` n'existe pas chez arXiv (c'était un ancien nom erroné). | Corrigé dans le code vers `export.arxiv.org/api/query`. Vous n'avez pas besoin de VPN ni de modifier `/etc/resolv.conf`. |
| `ModuleNotFoundError: No module named 'deap'` | Exécution locale sans avoir activé l'environnement virtuel. | Activez l'environnement : `source /tmp/genetic_venv/bin/activate` ou utilisez la méthode Docker. |

---

## ✅ Checklist Personnelle pour l'Utilisateur

Cochez au fur et à mesure de votre progression :

- [ ] **Docker** : Actif et utilisable sans `sudo` (`docker ps` fonctionne).
- [ ] **GitHub Token** : Créé sur GitHub et ajouté dans `.env` (`GITHUB_TOKEN=...`).
- [ ] **Optimisation Génétique** : Exécutée (`./run_genetic_optimization.sh` ou `python3 genetic_optimization.py`).
- [ ] **Fichiers de sortie validés** : Présence de `optimized_hyperparameters.json` et `benchmark_report.txt`.
- [ ] **Scraper arXiv / GitHub** : Exécuté (`python3 real_implementations/scraper.py`) avec succès.
- [ ] **Cluster Distribué Docker** : Testé avec `docker-compose up -d` et vérification de `curl http://127.0.0.1:8000/health`.
