#!/usr/bin/env python3

"""
Tests unitaires pour le coordinator.
"""

import pytest
from fastapi.testclient import TestClient
from backend.coordinator.main import app

# Client pour tester l'API FastAPI
client = TestClient(app)

# Test pour vérifier que le coordinator répond à la santé
def test_health_check():
    """Teste l'endpoint /health."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

# Test pour recevoir les gradients
def test_receive_gradients():
    """Teste l'endpoint /gradients pour recevoir les gradients."""
    test_data = {
        "worker_id": "test_worker",
        "gradients": {"param_0": 0.1, "param_1": 0.2},
        "batch_size": 32
    }

    response = client.post("/gradients", json=test_data)
    assert response.status_code == 200
    assert response.json()["status"] == "success"

# Test pour récupérer les mises à jour
def test_send_gradient_update():
    """Teste l'endpoint /gradients/update/{worker_id}."""
    # Envoyer d'abord des gradients pour que le buffer ne soit pas vide
    test_data = {
        "worker_id": "test_worker",
        "gradients": {"param_0": 0.1, "param_1": 0.2},
        "batch_size": 32
    }
    client.post("/gradients", json=test_data)

    response = client.get("/gradients/update/test_worker")
    assert response.status_code == 200
    assert response.json()["success"] is True

# Test pour vérifier les erreurs
def test_receive_gradients_invalid_data():
    """Teste la gestion des erreurs pour des données invalides."""
    invalid_data = {"worker_id": "test_worker"}  # Manque les gradients

    response = client.post("/gradients", json=invalid_data)
    assert response.status_code in (400, 422)

# Test pour vérifier l'absence de gradients
def test_send_gradient_update_no_gradients():
    """Teste l'erreur si aucun gradient n'est trouvé."""
    response = client.get("/gradients/update/unknown_worker")
    assert response.status_code == 404