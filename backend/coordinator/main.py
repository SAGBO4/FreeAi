#!/usr/bin/env python3
"""
================================================================================
FreeAi Distributed Gradient Coordinator — FastAPI Real Service
================================================================================
Ce service FastAPI centralise et orchestre l'agrégation de gradients pour les workers :
1. `/gradients` (POST) : Reçoit les tenseurs/deltas de gradients calculés par chaque worker.
2. `/gradients/update/{worker_id}` (GET) : Retourne le delta agrégé moyen pour synchroniser
   les poids du modèle sur le worker.
3. `/health` (GET) : Sonde de disponibilité et de santé pour l'orchestrateur Docker/K8s.
================================================================================
"""

import os
import time
import logging
from typing import Dict, List, Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Configuration du logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("freeai.coordinator")

COORDINATOR_PORT = int(os.getenv("COORDINATOR_PORT", 8000))

# Modèles Pydantic pour la validation stricte des échanges
class GradientData(BaseModel):
    """Payload transmis par un worker contenant ses gradients et sa taille de lot."""
    worker_id: str
    gradients: Dict[str, float]
    batch_size: int


class GradientUpdate(BaseModel):
    """Payload retourné au worker contenant les gradients agrégés."""
    worker_id: str
    update: Dict[str, float]
    success: bool


# Initialisation de l'application FastAPI
app = FastAPI(
    title="FreeAi Gradient Coordinator",
    description="Coordinateur de calcul distribué pour FreeAi Mesh",
    version="1.0.0"
)

# Configuration CORS pour autoriser les requêtes cross-origin locales
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"]
)

# Buffer en mémoire vive des gradients en attente d'agrégation
gradients_buffer: Dict[str, List[GradientData]] = {}


@app.post("/gradients")
async def receive_gradients(data: GradientData):
    """
    Endpoint de réception des gradients d'un worker.
    Stocke le delta dans le buffer RAM du coordinateur.
    """
    try:
        logger.info(f"[COORDINATOR] Gradients reçus du worker {data.worker_id} (batch_size={data.batch_size})")

        if data.worker_id not in gradients_buffer:
            gradients_buffer[data.worker_id] = []
        gradients_buffer[data.worker_id].append(data)

        return JSONResponse(
            status_code=200,
            content={"status": "success", "message": "Gradients received and buffered in RAM"}
        )
    except Exception as e:
        logger.error(f"[COORDINATOR] Erreur de traitement des gradients : {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/gradients/update/{worker_id}")
async def send_gradient_update(worker_id: str):
    """
    Endpoint permettant à un worker de récupérer les gradients agrégés.
    Calcule la moyenne pondérée des gradients et purge le buffer local.
    """
    if worker_id not in gradients_buffer or not gradients_buffer[worker_id]:
        raise HTTPException(status_code=404, detail=f"Aucun gradient en attente pour {worker_id}")

    worker_batches = gradients_buffer[worker_id]
    total_samples = sum(b.batch_size for b in worker_batches) or 1

    # Agrégation réelle : moyenne pondérée des paramètres
    aggregated_gradients: Dict[str, float] = {}
    param_keys = set().union(*(b.gradients.keys() for b in worker_batches))

    for param in param_keys:
        weighted_sum = sum(b.gradients.get(param, 0.0) * b.batch_size for b in worker_batches)
        aggregated_gradients[param] = weighted_sum / total_samples

    # Purge du buffer pour libérer la RAM (Mode NÉANT)
    gradients_buffer[worker_id] = []

    logger.info(f"[COORDINATOR] Agrégation calculée pour {worker_id} ({len(aggregated_gradients)} paramètres)")
    return JSONResponse(
        status_code=200,
        content={
            "worker_id": worker_id,
            "update": aggregated_gradients,
            "success": True
        }
    )


@app.get("/health")
async def health_check():
    """Vérification de l'état de fonctionnement du coordinateur."""
    return JSONResponse(
        status_code=200,
        content={
            "status": "healthy",
            "active_workers": list(gradients_buffer.keys()),
            "timestamp": time.time()
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=COORDINATOR_PORT)