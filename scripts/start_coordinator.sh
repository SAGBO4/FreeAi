#!/bin/bash

# Activer l'environnement virtuel
source /home/lesaint/Rendue/FreeAi/venv/bin/activate

# Lancer le coordinator
uvicorn backend.coordinator.main:app --host 0.0.0.0 --port 8000 --reload