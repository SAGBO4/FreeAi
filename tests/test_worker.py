#!/usr/bin/env python3

"""
Tests unitaires pour le worker.
"""

import pytest
import unittest.mock
from backend.worker.worker import compute_gradients, send_gradients_to_coordinator, fetch_gradient_updates

# Mock pour les appels HTTP
@unittest.mock.patch("requests.post")
def test_send_gradients_to_coordinator_success(mock_post):
    """Teste l'envoi des gradients au coordinator avec succès."""
    mock_post.return_value.status_code = 200

    gradients = {"param_0": 0.1, "param_1": 0.2}
    success = send_gradients_to_coordinator(gradients, batch_size=32)
    assert success is True
    mock_post.assert_called_once()

@unittest.mock.patch("time.sleep")
@unittest.mock.patch("requests.post")
def test_send_gradients_to_coordinator_failure(mock_post, mock_sleep):
    """Teste l'envoi des gradients au coordinator avec échec."""
    mock_post.side_effect = Exception("Failed to connect")

    gradients = {"param_0": 0.1, "param_1": 0.2}
    success = send_gradients_to_coordinator(gradients, batch_size=32)
    assert success is False

@unittest.mock.patch("requests.get")
def test_fetch_gradient_updates_success(mock_get):
    """Teste la récupération des mises à jour avec succès."""
    mock_response = unittest.mock.Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"success": True, "update": {"param_0": 0.1}}
    mock_get.return_value = mock_response

    updates = fetch_gradient_updates()
    assert updates == {"param_0": 0.1}

@unittest.mock.patch("requests.get")
def test_fetch_gradient_updates_failure(mock_get):
    """Teste la récupération des mises à jour avec échec."""
    mock_get.side_effect = Exception("Failed to connect")

    updates = fetch_gradient_updates()
    assert updates == {}

# Test pour vérifier le calcul des gradients
def test_compute_gradients():
    """Teste le calcul des gradients."""
    from backend.worker.worker import SimpleModel

    model = SimpleModel()
    gradients = compute_gradients(model, batch_size=32)
    assert isinstance(gradients, dict)
    assert len(gradients) > 0