# Problèmes connus

Bugs, limites, dette et points de sécurité encore ouverts. Une ligne corrigée reste, avec sa date et son commit.

| Id | Type | Resume | Ou | Repro | Gravité | Statut | Trouvé |
|---|---|---|---|---|---|---|---|
| KI-001 | Limite | Mode cloud F-37 : Inngest Cloud totalement vérifié de bout en bout en conditions réelles. L'application `freeai-sovereign-conduit` et la fonction durable `resilient-swarm-cascade` ont été synchronisées avec succès (`PUT /api/inngest` HTTP 200), l'événement `freeai/resilient.swarm.requested` (`01M5CZPN842F3ZPP4BVZJ7DKYS`) a été émis vers Inngest Cloud, et Inngest a rappelé le webhook sécurisé en exécutant les étapes durables (`POST /api/inngest` HTTP 200). Le sous-serveur isolé (port 8005) protège hermétiquement les routes locales (`/execute` retourne 404). | `app/orchestrator/inngest_conduit.py` | Résolu par isolation de port 8005 et synchronisation bidirectionnelle prouvée en direct. | Moyenne | Résolu | 2026-10-20 |
