# Spécification de l'API pour le Système de Gradients Distribué

## Introduction
Ce document décrit les endpoints HTTP utilisés par le système de calcul de gradients distribué.

## Endpoints du Coordinator

### 1. Endpoint `/gradients`
**Méthode :** POST
**Description :** Reçoit les gradients calculés par les workers.
**Requêtes :**
```json
{
    "worker_id": "string",
    "gradients": {
        "param_1": float,
        "param_2": float,
        ...
    },
    "batch_size": int
}
```
**Réponses :**
- **200 OK :** Succès
  ```json
  {
      "status": "success",
      "message": "Gradients received"
  }
  ```
- **400 Bad Request :** Données invalides

### 2. Endpoint `/gradients/update/{worker_id}`
**Méthode :** GET
**Description :** Retourne les mises à jour des gradients agrégés pour un worker.
**Réponses :**
- **200 OK :** Succès
  ```json
  {
      "worker_id": "string",
      "update": {
          "param_1": float,
          "param_2": float,
          ...
      },
      "success": true
  }
  ```
- **404 Not Found :** Aucun gradient trouvé pour le worker

### 3. Endpoint `/health`
**Méthode :** GET
**Description :** Vérifie l'état du coordinator.
**Réponses :**
- **200 OK :** Coordinator en bonne santé
  ```json
  {
      "status": "healthy"
  }
  ```

## Endpoints du Worker

### Communication avec le Coordinator
- **Envoyer les gradients :** `POST http://<coordinator_url>/gradients`
- **Récupérer les mises à jour :** `GET http://<coordinator_url>/gradients/update/{worker_id}`

## Gestion des Erreurs
- **Réessais et Backoff :** Les workers et le coordinator utilisent un mécanisme de réessai avec backoff exponentiel pour gérer les erreurs.
- **Logs :** Les erreurs sont loggées avec des détails pour le débogage.

## Configuration
- **Port du Coordinator :** `8000`
- **URL du Coordinator :** `http://localhost:8000` (à configurer selon l'environnement)
- **ID du Worker :** Définie par l'environnement (`WORKER_ID`)

## Exemple d'Utilisation
1. **Worker :** Calcule les gradients pour un batch et les envoie au coordinator.
2. **Coordinator :** Agrège les gradients et retourne les mises à jour.
3. **Worker :** Applique les mises à jour et répète le processus.

---