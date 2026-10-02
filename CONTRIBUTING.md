# Guide de Contribution à FreeAI ⚡

Merci de votre intérêt pour **FreeAI** ! Ce projet est un environnement d'intelligence artificielle souverain, conçu avec une rigueur technique absolue, une frugalité matérielle poussée à l'extrême (Mode NÉANT en RAM) et des règles de sécurité non négociables.

---

## 🏛️ Principes Fondamentaux

Toute contribution doit respecter les quatre piliers fondamentaux de FreeAI :

1. **Mode NÉANT (Zéro Écriture Disque)** :
   - Aucun fichier temporaire, log ou archive d'historique ne doit être écrit sur le disque local physique (SSD).
   - Utilisez systématiquement les flux en mémoire vive (`io.BytesIO`, `tmpfs`, `memfd_create`).
2. **Sanctuaire de la Vie Humaine (`SacredLifeSentinel`)** :
   - Aucune fonctionnalité ne doit contourner, atténuer ou dégrader la détection des intentions néfastes.
   - Les actions touchant aux infrastructures de survie, médicales ou à l'intégrité des personnes sont proscrites.
3. **Frugalité Matérielle (< 45 Mo RAM en veille, 0% CPU)** :
   - Déportez les calculs lourds vers les essaims cloud (`AETHER-SWARM`) plutôt que de surcharger le processeur local de l'utilisateur.
4. **Langues du Projet** :
   - **Code & Identificateurs** : Rédigés en anglais (classes, méthodes, fonctions, variables).
   - **Documentation & Messages Utilisateur** : Rédigés en français (`fr`).

---

## 🛠️ Processus de Développement & Branches

### Structure des Branches
- `main` : Branche de production stable, protégée, chaque commit y est audité et testé.
- `dev` : Branche d'intégration active pour les nouvelles fonctionnalités et expérimentations.
- `feat/<nom-fonctionnalite>` : Branches éphémères pour les développements spécifiques.

### Étapes de Contribution

1. **Forkez ou créez votre branche de travail** :
   ```bash
   git checkout dev
   git checkout -b feat/nouvelle-amelioration
   ```

2. **Écrivez d'abord vos tests (TDD)** :
   - Tout nouveau comportement ou correction de bug doit s'accompagner de tests unitaires ou d'intégration dans le répertoire `tests/`.
   - Assurez-vous que vos tests échouent avant la mise en œuvre (`red proof`) et passent avec succès après (`green`).

3. **Exécutez la suite de tests complète** :
   ```bash
   pytest -q
   ```
   *Tous les tests (actuellement 201 tests) doivent réussir sans avertissement critique.*

4. **Vérifiez la conformité Forge & Documentation** :
   ```bash
   python3 /home/lesaint/Rendue/forge/scripts/docs_check.py
   python3 /home/lesaint/Rendue/forge/scripts/tamper_check.py --base HEAD
   ```

5. **Style de Commits** :
   - Utilisez la convention *Conventional Commits* (`feat:`, `fix:`, `docs:`, `test:`, `refactor:`).
   - Tous les commits sont attribués à l'auteur principal et aux contributeurs officiels (sans mention de génération artificielle).

---

## 🔒 Règles de Sécurité lors des Contributions

- Ne commitez **jamais** de clés d'API réelles, de jetons Telegram ou d'identifiants de base de données dans le code.
- Utilisez toujours les variables d'environnement (`os.getenv(...)`) avec replis sécurisés.
- Ne modifiez pas l'intégrité de la sandbox `freeai-shadow` sans validation formelle.

---

## 📜 Licence

En contribuant à FreeAI, vous acceptez que vos contributions soient placées sous les termes de la [Licence MIT](LICENSE) du projet.
