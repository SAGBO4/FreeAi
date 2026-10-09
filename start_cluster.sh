#!/bin/bash

# Vérifier si docker-compose est installé
if ! command -v docker-compose &> /dev/null; then
    echo "Erreur: docker-compose n'est pas installé." >&2
    exit 1
fi

# Construire les images Docker
docker-compose build

# Lancer le cluster
docker-compose up -d

# Vérifier le statut des conteneurs
if docker-compose ps | grep -q "Up"; then
    echo "Le cluster FreeAI est opérationnel."
else
    echo "Erreur lors du démarrage du cluster." >&2
    exit 1
fi
