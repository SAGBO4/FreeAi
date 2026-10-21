#!/bin/bash

# Activer l'environnement virtuel
source /home/lesaint/Rendue/FreeAi/venv/bin/activate

# Lancer un worker avec un ID personnalisé
WORKER_ID=$1 python backend/worker/worker.py