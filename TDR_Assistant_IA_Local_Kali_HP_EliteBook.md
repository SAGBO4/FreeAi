# TDR — Assistant IA personnel local
## HP EliteBook · Kali Linux · CPU uniquement · 10 Go RAM

**Version : 1.0**  
**Architecture : 100 % locale / offline**  
**RAM maximale du système IA : 4 Go**  
**RAM cible : 3,5 Go maximum**

---

# 1. Objectif du projet

Créer un assistant IA personnel fonctionnant entièrement sur le **HP EliteBook de l'utilisateur sous Kali Linux**, sans dépendance obligatoire à Internet ni à une API cloud mais peux use internet .

L'assistant doit être capable de :

- comprendre des instructions textuelles  ;
- travailler avec les projets locaux ;
- utiliser VS Code et le terminal ;
- lire, créer et modifier des fichiers ;
- exécuter des commandes et des tests ;
- utiliser Git ;
- orchestrer plusieurs agents spécialisés ;
- aider à créer des applications complètes ;
- analyser et tester la sécurité des projets appartenant à l'utilisateur ;
- travailler avec des applications et outils installés sur le PC ;
- conserver une mémoire locale si besoin;
- fonctionner entièrement sur CPU ;
- rester sous une limite stricte de **4 Go de RAM pour l'ensemble du système IA**.

Le but n'est pas de créer un énorme modèle comparable à un service cloud.

Le but est de créer :

> **un petit modèle local + un orchestrateur puissant + des outils locaux + des agents spécialisés + une mémoire locale + un contrôle strict des ressources avec une liberté sans verroue total**

---

# 2. Matériel cible

## Ordinateur

- **HP pavilion**
- **10 Go de RAM**
- **Kali Linux**
- **CPU uniquement**
- Aucun GPU nécessaire

Le système doit être conçu pour cette machine réelle.

Les performances doivent être mesurées directement sur le HP Pavilion avant de considérer le système comme validé.

---

# 3. Contraintes non négociables

| Élément | Exigence |
|---|---|
| OS | Kali Linux |
| Machine | HP Pavilion |
| RAM totale | 10 Go |
| GPU | Aucun |
| Calcul | CPU |
| Mode | Local / offline | online si besoin de ressource
| API cloud | Non requise |
| RAM IA cible | ≤ 3,5 Go |
| RAM IA absolue | **≤ 4 Go** |
| Réseau | Si BESOIN si non ,Désactivé par défaut |
| Données | Locales et internet aussi |
| Mémoire | Locale |
| Modèle | Quantifié |
| Serveur | localhost uniquement mais peux communiquer avec les autre ia en ligne pour des solution|

Le système ne doit pas être conçu pour consommer 4 Go en permanence.

**3,5 Go est la cible normale.**

Les 500 Mo restants constituent une marge de sécurité.

---

# 4. Architecture générale

```text
                         UTILISATEUR
                              │
                     ┌────────┴────────┐
                     │                 │
                   VOIX              TEXTE
                     │                 │
                     └────────┬────────┘
                              ▼
                    ┌───────────────────┐
                    │ Interface locale  │
                    └─────────┬─────────┘
                              ▼
                    ┌───────────────────┐
                    │   ORCHESTRATEUR   │
                    │       LOCAL       │
                    └─────────┬─────────┘
                              │
              ┌───────────────┼────────────────┐
              ▼               ▼                ▼
        Agent Code      Agent Sécurité    Agent Git
              │               │                │
              └───────────────┼────────────────┘
                              ▼
                    ┌───────────────────┐
                    │     LLM LOCAL     │
                    │   CPU / quantifié │
                    └─────────┬─────────┘
                              ▼
                     ┌────────────────┐
                     │  TOOL GATEWAY  │
                     └───────┬────────┘
                             │
        ┌────────────────────┼────────────────────┐
        ▼                    ▼                    ▼
     Fichiers             Terminal              Git
        │                    │                    │
        └────────────────────┼────────────────────┘
                             ▼
                       Projets locaux
```

---

# 5. Philosophie d'autonomie

L'utilisateur souhaite un agent **très autonome**, et non un simple chatbot qui demande constamment une validation.

Le système doit donc prévoir un **Mode Autonome**.

Dans ce mode, l'agent peut utiliser tous les outils qui lui sont explicitement exposés.

Cela peut inclure :

- système de fichiers ;
- terminal ;
- Git ;
- VS Code/workspaces ;
- outils de développement ;
- tests ;
- analyse de sécurité ;
- outils réseau de laboratoire ;
- navigateur local ou outils de test si configurés ;
- scripts ;
- outils ajoutés ultérieurement.

L'agent doit pouvoir enchaîner plusieurs actions pour atteindre l'objectif.

Exemple :

```text
Créer une application
        ↓
Créer les fichiers
        ↓
Installer les dépendances
        ↓
Configurer le projet
        ↓
Lancer les tests
        ↓
Lire les erreurs
        ↓
Modifier le code
        ↓
Relancer les tests
        ↓
Analyser le résultat
        ↓
Préparer le projet
```

---

# 6. Autonomie et contrôle humain

L'agent doit être libre dans son raisonnement et dans l'utilisation des outils qui lui sont exposés.

Cependant :

> **Autonomie ne signifie pas absence de visibilité.**

L'utilisateur doit toujours pouvoir :

- voir les actions ;
- voir les commandes ;
- voir les fichiers modifiés ;
- voir les résultats ;
- consulter les logs ;
- interrompre l'agent ;
- arrêter un worker ;
- arrêter l'orchestrateur ;
- reprendre la main.

L'objectif est donc :

> **Autonomie maximale + transparence maximale + possibilité d'arrêt immédiat.**

---

# 7. Modes de fonctionnement

## 7.1 Mode Normal

Utilisation quotidienne.

```text
Assistant
→ projets locaux
→ fichiers
→ terminal
→ Git
→ développement
```

---

## 7.2 Mode Autonome

L'agent peut enchaîner librement les outils autorisés.

```text
Utilisateur
→ objectif

Agent
→ planification
→ exécution
→ vérification
→ correction
→ résultat
```

---

## 7.3 Mode LAB

Environnement expérimental isolé.

Utilisation :

- tests avancés ;
- tests de sécurité ;
- expériences ;
- scripts potentiellement destructifs ;
- tests dynamiques ;
- simulations.

Le laboratoire doit idéalement disposer de :

- snapshots ;
- rollback ;
- workspace séparé ;
- données de test ;
- logs complets.

Architecture :

```text
Mode LAB
    │
    ├── Projet de test
    ├── Base de données de test
    ├── Services de test
    └── Environnement isolé
```

---

# 8. Modèle IA local

Le système doit utiliser un **petit modèle quantifié**, adapté au CPU.

Formats possibles :

- GGUF ;
- runtime compatible llama.cpp ;
- autre runtime CPU local équivalent.

Le choix du modèle doit être fait après benchmark.

Le fichier du modèle n'est pas le seul élément à prendre en compte.

Il faut mesurer :

- RSS ;
- mémoire du contexte ;
- mémoire du runtime ;
- mémoire des agents ;
- mémoire des outils ;
- mémoire du STT ;
- pics de consommation.

---

# 9. Budget RAM

Budget de conception :

```text
LLM quantifié             2,0 – 2,8 Go
Contexte / runtime        0,3 – 0,6 Go
Orchestrateur + agents    0,2 – 0,4 Go
Speech-to-text            0,3 – 0,5 Go
Tool Gateway              0,2 – 0,3 Go
-----------------------------------------
Cible totale              ≤ 3,5 Go
Limite absolue            ≤ 4,0 Go
```

Ces chiffres sont des budgets et doivent être validés par benchmark.

---

# 10. Resource Manager

Le système doit posséder un gestionnaire de ressources.

Fonctions :

```python
get_memory_usage()
check_memory_budget()
check_cpu_usage()
reduce_context()
stop_optional_worker()
shutdown_ai_worker()
```

Comportement :

```text
< 3,5 Go
→ fonctionnement normal

3,5 – 4 Go
→ mode dégradé
→ réduire les tâches secondaires
→ réduire le contexte si nécessaire

> 4 Go
→ arrêt contrôlé du worker IA
```

Le dépassement doit être détecté automatiquement.

---

# 11. CPU

Le système doit fonctionner sans GPU.

Le nombre de threads doit être configurable :

```env
LLM_THREADS=4
```

Cette valeur est un point de départ.

Elle doit être ajustée après benchmark du HP EliteBook.

Le but n'est pas d'utiliser 100 % du CPU en permanence.

Le système doit privilégier :

- stabilité ;
- réactivité ;
- température raisonnable ;
- consommation RAM contrôlée.

---

# 12. Contexte du modèle

Le contexte doit rester limité.

Exemple initial :

```env
LLM_CONTEXT_SIZE=4096
```

Ne pas utiliser immédiatement des contextes gigantesques.

La mémoire historique doit être récupérée intelligemment au lieu d'être injectée entièrement dans chaque prompt.

---

# 13. Orchestrateur

L'orchestrateur est le cerveau du système.

Responsabilités :

- comprendre l'objectif ;
- choisir l'agent ;
- choisir les outils ;
- planifier les étapes ;
- exécuter les tâches ;
- vérifier les résultats ;
- relancer une tâche si nécessaire ;
- gérer les erreurs ;
- retourner un résultat à l'utilisateur.

Exemple :

```text
Utilisateur :
"Analyse mon projet et corrige les erreurs."

Orchestrateur :
→ Agent Code
→ analyse fichiers
→ lance tests
→ récupère erreurs
→ corrige
→ relance tests
→ rapport
```

---

# 14. Agents

## 14.1 Agent Code

Responsabilités :

- lire le code ;
- comprendre l'architecture ;
- créer des fichiers ;
- modifier du code ;
- supprimer du code ;
- lancer les tests ;
- corriger les erreurs ;
- analyser les logs ;
- travailler sur plusieurs fichiers ;
- préparer une fonctionnalité.

---

## 14.2 Agent Git

Responsabilités :

```text
git status
git diff
git log
git branch
git checkout
git add
git commit
```

Les opérations distantes doivent être configurables.

---

## 14.3 Agent Sécurité

L'agent sécurité doit permettre l'audit des projets de l'utilisateur.

Il peut effectuer :

### Analyse statique

- code source ;
- dépendances ;
- secrets ;
- configurations ;
- endpoints ;
- authentification ;
- autorisation ;
- validation des entrées ;
- erreurs de configuration.

### Analyse dynamique

Sur une application appartenant à l'utilisateur ou un environnement explicitement autorisé :

```text
URL
 ↓
Discovery
 ↓
Tests
 ↓
Validation
 ↓
Evidence
 ↓
Rapport
```

Les tests destructifs sont réservés au Mode LAB.

---

# 15. Audit de sécurité complet

L'objectif est de permettre à l'agent de tester sérieusement le projet de l'utilisateur.

Le système peut combiner :

```text
SAST
+
Dependency scanning
+
Secret scanning
+
Configuration review
+
Dynamic testing
+
Manual reasoning by LLM
```

Le rapport doit distinguer :

- vulnérabilité confirmée ;
- suspicion ;
- faux positif possible ;
- information insuffisante.

Il ne doit pas présenter une hypothèse comme une vulnérabilité confirmée.

---

# 16. Rapport de sécurité

Format recommandé :

```text
ID
Sévérité
Composant
Type
Description
Preuve
Impact
Étapes de reproduction
Correction
Référence
Statut
```

Exemple :

```text
SEC-001

Severity:
High

Component:
POST /api/users

Issue:
Authorization failure

Evidence:
...

Impact:
...

Reproduction:
...

Recommendation:
...

Status:
Confirmed
```

---

# 17. Tool Gateway

Tous les outils passent par une couche commune.

Exemples :

```text
filesystem
terminal
git
tests
security
process
memory
browser
```

Chaque outil possède :

- nom ;
- schéma ;
- timeout ;
- logs ;
- limites ;
- permissions ;
- résultat structuré.

Le Tool Gateway ne doit pas transformer chaque action en validation manuelle obligatoire.

Il doit surtout fournir :

- exécution ;
- observabilité ;
- contrôle des ressources ;
- arrêt ;
- logs.

---

# 18. Système de fichiers

Le système doit pouvoir travailler sur les projets de l'utilisateur.

Exemple :

```text
/home/<user>/Projects/
```

Le workspace peut contenir :

```text
TelegramBot/
SaaS/
etc.
```

Le système doit connaître le workspace courant.

---

# 19. Terminal

L'agent doit pouvoir exécuter des commandes Linux.

Exemples :

```bash
npm install
npm run dev
npm test
python main.py
pytest
git status
docker compose up
```

Les commandes doivent être journalisées.

Les commandes longues doivent avoir un timeout configurable.

---

# 20. VS Code

L'assistant doit pouvoir travailler avec les projets ouverts dans VS Code.

Le MVP peut fonctionner directement sur les fichiers et le terminal.

Une extension VS Code pourra ensuite fournir :

- chat ;
- sélection de code ;
- actions rapides ;
- affichage des tâches ;
- logs ;
- statut de l'agent ;
- interruption.



---

# 22. Mémoire

La mémoire doit rester locale.

Technologie initiale :

```text
SQLite
+
fichiers locaux
```

Organisation :

```text
memory/
├── preferences.db
├── projects.db
├── conversations.db
└── embeddings/
```

Ne jamais charger toute la mémoire dans le contexte du LLM.

Utiliser une récupération ciblée.

---

# 23. Mode offline

Le fonctionnement normal doit rester possible sans Internet.

Le système ne doit pas dépendre de :

- OpenAI ;
- Google AI ;
- Anthropic ;
- API cloud STT ;
- API cloud TTS ;
- services cloud de sécurité ;
- télémétrie obligatoire.

Les modèles et dépendances nécessaires sont installés localement.

---

# 24. Réseau

Par défaut :

```env
ALLOW_NETWORK=false si besoin il peu switché à true
```

Le cœur de l'assistant écoute uniquement :

```text
127.0.0.1
```

Exemple :

```env
SERVER_HOST=127.0.0.1
SERVER_PORT=8000
```

Aucun service ne doit être exposé publiquement par défaut.

Pour les tests de sécurité d'une application de l'utilisateur, le réseau peut être activé dans un environnement de test explicitement configuré.

---

# 25. Configuration

Exemple :

```env
LLM_MODEL_PATH=./models/model.gguf

LLM_CONTEXT_SIZE=4096
LLM_THREADS=4

RAM_TARGET_MB=3500
RAM_HARD_LIMIT_MB=4000

SERVER_HOST=127.0.0.1
SERVER_PORT=8000

OFFLINE_MODE=true
ALLOW_NETWORK=false
ALLOW_SUDO=true

WORKSPACE_ROOT=/home/<user>/Projects
```

---

# 26. Privilèges système

L'agent doit fonctionner normalement sans root.

```env
ALLOW_SUDO=false
```

L'accès root ne doit jamais être considéré comme nécessaire au fonctionnement normal.

Si une tâche nécessite exceptionnellement des privilèges supplémentaires, elle doit être clairement identifiée.

---

# 27. Observabilité

L'utilisateur doit pouvoir suivre l'agent.

Logs :

```text
logs/
├── orchestrator.log
├── agent_code.log
├── agent_security.log
├── tools.log
├── memory.log
└── errors.log
```

Chaque action importante doit pouvoir être retrouvée.

Exemple :

```text
[10:31:05]
Agent Code

Tool:
terminal

Command:
npm test

Result:
12 passed / 1 failed
```

---

# 28. Interruption

L'utilisateur doit pouvoir arrêter l'agent.

Exemple :

```text
CTRL+C
```

ou bouton :

```text
STOP AGENT
```

L'arrêt doit :

- stopper le worker ;
- stopper les tâches enfants ;
- fermer proprement les processus ;
- conserver les logs.

---

# 29. Sécurité du système

Le système doit empêcher le modèle de produire directement une commande arbitraire qui serait exécutée sans traitement.

Pipeline :

```text
LLM
 ↓
Tool Call
 ↓
Validation
 ↓
Execution
 ↓
Result
 ↓
LLM
```

---

# 30. Protection contre les erreurs de l'agent

L'agent peut se tromper.

Le système doit donc prévoir :

- timeout ;
- limite de sortie ;
- limite RAM ;
- limite CPU ;
- logs ;
- rollback ;
- arrêt manuel ;
- workspace de test.

---

# 31. Rollback

Pour les modifications importantes :

```text
Projet
 ↓
Snapshot / Git checkpoint
 ↓
Agent travaille
 ↓
Tests
 ↓
Validation
```

En cas d'échec :

```text
Rollback
```

---

# 32. Structure du projet

```text
local-ai/
│
├── app/
│   ├── main.py
│   │
│   ├── orchestrator/
│   │   ├── orchestrator.py
│   │   ├── planner.py
│   │   └── router.py
│   │
│   ├── agents/
│   │   ├── code_agent.py
│   │   ├── security_agent.py
│   │   ├── git_agent.py
│   │   └── base_agent.py
│   │
│   ├── llm/
│   │   ├── runtime.py
│   │   ├── model.py
│   │   └── prompts.py
│   │
│   ├── tools/
│   │   ├── filesystem.py
│   │   ├── terminal.py
│   │   ├── git.py
│   │   ├── testing.py
│   │   └── security.py
│   │
│   ├── security/
│   │   ├── scanner.py
│   │   ├── scope.py
│   │   └── report.py
│   │
│   ├── memory/
│   │   ├── database.py
│   │   ├── retrieval.py
│   │   └── embeddings.py
│   │
│   ├── voice/
│   │   ├── stt.py
│   │   └── tts.py
│   │
│   └── resource_manager/
│       ├── memory.py
│       ├── cpu.py
│       └── watchdog.py
│
├── models/
├── config/
├── tests/
├── scripts/
├── logs/
├── memory/
│
├── requirements.txt
├── .env
└── README.md
```

---

# 33. Technologies proposées

## Backend

```text
Python
```

## LLM

```text
llama.cpp
ou runtime CPU local équivalent
```

## Modèle

```text
GGUF quantifié
```

## API locale

```text
FastAPI
```

## Validation

```text
Pydantic
```

## Monitoring

```text
psutil
```

## Mémoire

```text
SQLite
```

## Versioning

```text
Git
```

---

# 34. Phase 1 — Benchmark

Ne pas commencer directement par tous les agents.

Commencer par tester plusieurs petits modèles.

Mesurer :

```text
RAM
CPU
tokens/sec
temps de réponse
qualité
tool calling
```

Tests :

```text
Test 1 :
question simple

Test 2 :
raisonnement

Test 3 :
lecture de code

Test 4 :
tool calling

Test 5 :
enchaînement de plusieurs outils

Test 6 :
long contexte
```

---

# 35. Phase 2 — LLM local

Installer :

- runtime ;
- modèle ;
- monitoring ;
- configuration CPU ;
- limite RAM.

Objectif :

```text
Prompt
→ réponse locale
```

Puis :

```text
Prompt
→ Tool Call
→ résultat
→ réponse
```

---

# 36. Phase 3 — Tool Gateway

Créer :

```text
filesystem
terminal
git
testing
```

Tester chaque outil indépendamment.

---

# 37. Phase 4 — Orchestrateur

Créer :

```text
Router
Planner
Executor
Memory
Resource Manager
```

L'orchestrateur devient le point central.

---

# 38. Phase 5 — Agent Code

Objectif :

```text
"Crée une API FastAPI"

→ création du projet
→ fichiers
→ dépendances
→ tests
→ correction
→ résultat
```

---

# 39. Phase 6 — Agent Sécurité

Ajouter :

```text
SAST
Dependency scanning
Secret scanning
Configuration analysis
Dynamic testing
Security reporting
```

Les tests avancés doivent être réalisés sur les projets et environnements appartenant à l'utilisateur ou explicitement autorisés.

---

# 40. Phase 7 — Voix

Ajouter :

```text
STT local
TTS local
```

Puis mesurer à nouveau la RAM.

Si la voix fait dépasser le budget :

```text
réduire le modèle STT
ou
charger le composant uniquement pendant son utilisation
```

---

# 41. Phase 8 — Mode LAB

Créer un environnement isolé.

Objectifs :

- tests avancés ;
- expérimentation ;
- sécurité ;
- rollback ;
- observation.

---

# 42. Phase 9 — Optimisation

Mesurer :

```text
RAM minimum
RAM moyenne
RAM maximum
CPU moyen
CPU maximum
temps de réponse
```

Optimiser ensuite :

- taille du modèle ;
- quantification ;
- contexte ;
- nombre de threads ;
- chargement à la demande ;
- mémoire ;
- agents.

---

# 43. Critères d'acceptation

Le projet est validé si :

- [ ] fonctionne sur Kali Linux ;
- [ ] fonctionne sur le HP EliteBook ;
- [ ] ne nécessite aucun GPU ;
- [ ] fonctionne hors ligne ;
- [ ] RAM cible ≤ 3,5 Go ;
- [ ] RAM absolue ≤ 4 Go ;
- [ ] watchdog RAM fonctionnel ;
- [ ] assistant vocal local ;
- [ ] LLM local ;
- [ ] mémoire locale ;
- [ ] orchestrateur fonctionnel ;
- [ ] Agent Code fonctionnel ;
- [ ] Agent Git fonctionnel ;
- [ ] Agent Sécurité fonctionnel ;
- [ ] Tool Gateway fonctionnel ;
- [ ] travail sur VS Code/workspace possible ;
- [ ] terminal utilisable ;
- [ ] tests exécutables ;
- [ ] logs disponibles ;
- [ ] interruption possible ;
- [ ] Mode Autonome fonctionnel ;
- [ ] Mode LAB fonctionnel ;
- [ ] rollback possible ;
- [ ] aucune dépendance cloud obligatoire.

---

# 44. Test final de RAM

Le test final doit être réalisé directement sur le HP EliteBook.

Scénario :

```text
1. Démarrer l'assistant.
2. Mesurer la RAM avant chargement.
3. Charger le LLM.
4. Mesurer la RAM.
5. Activer l'orchestrateur.
6. Activer un agent.
7. Faire travailler l'agent sur un projet.
8. Exécuter des tests.
9. Faire une analyse de sécurité.
10. Tester la voix.
11. Observer le pic RAM.
```

Résultat attendu :

```text
PIC RAM IA < 4 Go
```

Résultat idéal :

```text
PIC RAM IA ≤ 3,5 Go
```

---

# 45. Principe final

Le système ne doit pas chercher à remplacer les grands modèles cloud par un modèle gigantesque.

Il doit exploiter intelligemment les ressources limitées du HP EliteBook.

Architecture finale :

```text
             PETIT LLM LOCAL
                    │
                    ▼
              ORCHESTRATEUR
                    │
        ┌───────────┼───────────┐
        ▼           ▼           ▼
      CODE       SECURITY       GIT
        │           │           │
        └───────────┼───────────┘
                    ▼
              TOOL GATEWAY
                    │
       ┌────────────┼────────────┐
       ▼            ▼            ▼
    FICHIERS      TERMINAL      TESTS
                    │
                    ▼
              PROJETS LOCAUX
```

La puissance du système vient principalement de **l'orchestration et des outils**, pas uniquement de la taille du modèle.

---

# 46. Première action à réaliser

Avant de développer les agents :

```text
ÉTAPE 1
→ identifier le CPU exact du HP Pavilion

ÉTAPE 2
→ vérifier les 10 Go de RAM

ÉTAPE 3
→ vérifier l'espace disque disponible

ÉTAPE 4
→ installer le runtime local

ÉTAPE 5
→ tester plusieurs petits modèles quantifiés

ÉTAPE 6
→ mesurer la RAM réelle

ÉTAPE 7
→ choisir le modèle

ÉTAPE 8
→ construire le Tool Gateway

ÉTAPE 9
→ construire l'orchestrateur

ÉTAPE 10
→ ajouter les agents
```

**Ne pas choisir le modèle uniquement selon la taille de son fichier.**

Le modèle final doit être choisi selon son comportement réel sur le HP EliteBook.

---

# 47. Résultat attendu

À terme, l'utilisateur doit pouvoir dire localement :

> « Ouvre mon projet MaoCodes, regarde ce qui reste à faire, analyse le code, corrige les erreurs, lance les tests et donne-moi le résultat. »

Ou :

> « Analyse cette application que j'ai déployée, effectue un audit de sécurité complet dans mon environnement de test, vérifie les vulnérabilités que tu peux confirmer et prépare-moi un rapport avec les corrections. »

L'assistant doit alors :

```text
Comprendre
   ↓
Planifier
   ↓
Choisir les agents
   ↓
Utiliser les outils
   ↓
Exécuter
   ↓
Observer
   ↓
Tester
   ↓
Corriger
   ↓
Vérifier
   ↓
Rapporter
```

Le tout :

```text
HP Pavilion
+
Kali Linux
+
CPU
+
10 Go RAM
+
LLM local
+
≤ 4 Go RAM pour l'IA
+
Aucun cloud obligatoire
```

---

# 48. Règle fondamentale du projet

> **Construire un agent réellement autonome, local et utile, sans sacrifier la stabilité du HP EliteBook.**

La priorité technique est :

```text
STABILITÉ
    ↓
RAM ≤ 4 Go
    ↓
AUTONOMIE
    ↓
OUTILS
    ↓
AGENTS
    ↓
QUALITÉ DU MODÈLE
```

