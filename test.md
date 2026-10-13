# 🧪 test.md — Comment vérifier toi-même que chaque fonctionnalité marche vraiment

Ce document te donne, pour chaque fonctionnalité listée dans `docs/explain.md`, une
commande précise à lancer toi-même sur ta machine, ce que tu dois voir si ça marche,
et ce que ça veut dire si ça échoue. Tout est pensé pour que tu puisses vérifier par
toi-même, sans me faire confiance sur parole.

## Avant de commencer : lancer toute la suite d'un coup

```bash
cd /home/lesaint/Rendue/FreeAi
python3 -m pytest tests/ -q
```
Si tu vois `X passed` sans `failed` à la fin (hors le test ultrasonique qui peut
parfois nécessiter un deuxième essai, voir point 18), tout le projet est dans l'état
attendu. Ça prend environ 9-10 minutes (tests réseau et audio réels inclus).

Pour tester UNE SEULE fonctionnalité sans attendre toute la suite, utilise les
commandes ciblées ci-dessous.

---

## 🟢 Modules réels

### 1. Cluster de Calcul Distribué de Gradients
```bash
python3 -m pytest tests/test_coordinator.py tests/test_worker.py -v
```
Si tu veux le voir tourner en vrai :
```bash
docker-compose up --build -d
curl http://127.0.0.1:8000/health
```
Tu dois voir `{"status": "healthy", ...}`. Pour arrêter : `docker-compose down`.

### 2. L'Anneau Neuronal LAN P2P
```bash
python3 -m pytest tests/test_neural_ring_real.py -v
```
Tous les tests doivent passer : ils vérifient un vrai calcul de tenseurs NumPy,
pas un texte simulé.

### 3. Cyber-Hermes & Registre d'Outils Kali Linux
```bash
python3 -m pytest tests/test_kali_hermes_real.py tests/test_freeai_cyber.py -v
```
Pour le voir en vrai (si tu as des outils Kali installés) :
```bash
python3 freeai_cyber.py --interactive
```

### 4. Proxy LiteLLM Sovereign Mesh
```bash
./scripts/start_claude_litellm.sh &
curl http://127.0.0.1:4000/health
```
Tu dois voir une réponse JSON listant les modèles disponibles. Arrête ensuite le
processus avec `kill %1` ou `Ctrl+C` si lancé au premier plan.

### 5. Extracteur d'Intelligence Scientifique (arXiv / GitHub)
```bash
python3 real_implementations/scraper.py
cat real_implementations/scraped_data/arxiv_data.json | head -30
```
Tu dois voir de vrais titres d'articles récents avec dates et auteurs, pas des
données figées.

### 6. Optimiseur Génétique Darwinien
```bash
./run_genetic_optimization.sh
```
Attends quelques minutes : un fichier `optimized_hyperparameters.json` doit
apparaître à la fin avec de vraies valeurs mesurées (pas des valeurs par défaut).

### 7. SatelliteEye
```bash
python3 -m pytest tests/test_satellite_eye.py -v
```
Ces tests font de vrais appels aux APIs OpenSky/NASA/Open-Meteo : s'ils échouent
avec une erreur réseau, vérifie ta connexion Internet avant de conclure à un bug.

### 8. Mémoire Hyperdimensionnelle (HDC)
```bash
python3 -m pytest tests/test_vortex_aether.py -k BinaryHologram -v
```

### 9. Radar de Bounties GitHub & Création Réelle de Correctifs
```bash
python3 -m pytest tests/test_bounty_radar.py -v
```
⚠️ Ces tests ne créent pas de vraie Pull Request sur un vrai dépôt (ils mockent
l'étape finale d'envoi) — c'est volontaire pour ne rien soumettre par accident.

### 10. Moteur Vidéo & Showcase Automatique
```bash
python3 -m pytest tests/test_video_engine.py tests/test_brag_engine.py -v
```

### 11. Sovereign Search
```bash
python3 -m pytest tests/test_sovereign_search.py -v
```

### 12. La Résultante Souveraine (Audit de Sécurité Unifié)
```bash
python3 -m pytest tests/test_sovereign_resultant.py -v
```

### 13. Conduit Vocal P2P Souverain
```bash
python3 -m pytest tests/test_sovereign_voice_conduit.py -v
```

### 14. Intercom Local Zéro-Touch
```bash
python3 -m pytest tests/test_zero_touch_intercom.py -v
```

### 15. Protocole Aether-Legion
```bash
python3 -m pytest tests/test_aether_legion.py -v
```

### 16. Aether-Swarm (Consensus Multi-Modèles Cloud)
```bash
python3 -m pytest tests/test_aether_swarm.py -v
```
Pour le voir en conditions réelles (consomme un peu de quota API Groq/OpenRouter) :
```bash
python3 -c "
import asyncio
from app.cluster.aether_swarm import AetherSwarmOrchestrator
from app.llm.federation import OnlineModelFederation

async def main():
    swarm = AetherSwarmOrchestrator(federation=OnlineModelFederation())
    res = await swarm.execute_swarm_objective('Faut-il utiliser PostgreSQL ou MongoDB ?')
    print(res['consensus']['synthesized_content'])
    print('Modèles ayant réellement répondu :', res['consensus']['participating_models'])

asyncio.run(main())
"
```
Tu dois voir dans `participating_models` uniquement des providers qui ont
vraiment répondu (jamais 3 noms fixes systématiquement).

### 17. Auto-Apply avec Revue Humaine en Direct
```bash
python3 -m pytest tests/test_auto_apply.py -v
```
Pour le tester en vrai (ouvre un vrai navigateur, consomme ~15 secondes) :
depuis le CLI interactif (`python3 cli.py`), ou en envoyant un message Telegram
au bot configuré, tape :
```
/apply-live 1
```
Tu dois recevoir un lien `http://<ton IP>:<port>/vnc.html?...`. Ouvre-le dans un
navigateur sur le même réseau Wi-Fi : tu dois voir un vrai formulaire de
candidature déjà rempli (nom, email, téléphone, lettre, CV joint), sans qu'aucun
bouton "Envoyer" n'ait été cliqué pour toi.

### 18. Transmission par Ultrasons Inaudibles
```bash
python3 -m pytest tests/test_vortex_aether.py::TestUltrasonicAirGapTransceiver -v
```
⚠️ Le test réel (`test_real_microphone_loopback_decode_via_pipewire`) utilise un
vrai micro et un vrai haut-parleur : la fiabilité d'un seul essai varie entre 50%
et 100% selon le bruit ambiant et l'état de ta carte son au moment du test (c'est
un vrai canal acoustique, pas une simulation parfaite) - le test retente jusqu'à
8 fois avant de déclarer un échec. S'il échoue malgré tout, relance-le une fois ;
s'il échoue systématiquement, dis-le-moi.

---

## 🟡 / 🔴 Modules encore simulés ou partiels (pour vérifier que les limites sont bien honnêtes, pas cachées)

### Free Cloud Pool
```bash
python3 -m pytest tests/test_free_cloud_pool.py -v
```
Les tests doivent passer, mais si tu regardes le code (`app/cluster/free_cloud_pool.py`),
tu dois voir qu'aucune vraie connexion SSH n'est établie - c'est attendu, documenté
dans `NEEDS.md`.

### Ghost Bridge
```bash
python3 -m pytest tests/test_sacred_life_and_apex_nexus.py -k Ghost -v
```

### Starlink Adapter
```bash
python3 -c "
import asyncio
from app.network.starlink_adapter import StarlinkAdapter
async def main():
    a = StarlinkAdapter()
    print(await a.get_signal_quality())
    print(await a.get_visible_satellites())
asyncio.run(main())
"
```
Tu dois voir `None` puis `0` : c'est le comportement honnête attendu sans antenne
physique branchée, pas une erreur.

### Télépathie Neuronale & Hypermesh Causal Singularity
```bash
python3 -m pytest tests/test_neural_telepathy.py tests/test_hypermesh_causal_singularity.py -v
```

### Onion Portal (Tor V3) - état honnête si Tor n'est pas disponible
```bash
python3 -m pytest tests/test_onion_portal.py -v
```
Le test `test_launch_tor_daemon_reports_pending_instead_of_fake_address` vérifie
spécifiquement qu'aucune fausse adresse `.onion` n'est jamais inventée.

---

## 🎯 Les 3 corrections de cette session, vérifiées en détail

Ces trois-là ont été spécifiquement vérifiées par un agent indépendant qui a
réintroduit l'ancien code défectueux pour confirmer que les tests le détectent :

```bash
python3 -m pytest tests/test_freeai_cyber.py::TestFreeAICyber::test_kali_tool_availability_reflects_real_detection_not_hardcoded_list -v
python3 -m pytest tests/test_onion_portal.py::test_launch_tor_daemon_reports_pending_instead_of_fake_address -v
python3 -m pytest tests/test_aether_swarm.py::test_swarm_no_fabrication_when_all_providers_fail tests/test_aether_swarm.py::test_swarm_consensus_reflects_only_real_responses -v
```
Les 4 doivent passer.

---

## En cas de doute sur un résultat

Si un test échoue et que tu ne sais pas si c'est un vrai bug ou un problème
d'environnement (réseau, clé API absente, outil non installé), copie-colle moi
la sortie complète de la commande - je lirai l'erreur avec toi plutôt que de
deviner.
