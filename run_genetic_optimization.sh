#!/bin/bash

# Vérifier si docker-compose est installé
if ! command -v docker-compose &> /dev/null; then
    echo "Erreur: docker-compose n'est pas installé." >&2
    exit 1
fi

# Construire l'image Docker du worker
docker-compose build worker1

# Lancer le conteneur Docker pour exécuter l'optimisation génétique
# Utiliser un conteneur dédié pour éviter les conflits avec les autres services
docker run --rm \
    --network freeai_network \
    -v $(pwd):/app \
    -w /app \
    freeai-worker \
    python genetic_optimization.py