# FreeAI ⚡

> **Sovereign Autonomous Cognitive Agent & Tactical Command Suite**  
> *Zero-Disk Footprint (Mode NÉANT) | Pure Volatile RAM Execution | Multi-Cloud Resilient Persistence*

---

## 🌟 Présentation

**FreeAI** est une plateforme d'intelligence artificielle souveraine conçue pour les développeurs, chercheurs en sécurité et ingénieurs exigeants. Elle fonctionne avec une frugalité extrême en mémoire vive (< 60 Mo en veille), sans résidu sur le disque SSD local (Mode NÉANT), et s'affranchit des verrous et de la censure arbitraire des solutions propriétaires.

---

##  Caractéristiques Clés

- **Mode NÉANT Inviolable** : 0 octet écrit sur le SSD. Toutes les opérations s'exécutent en RAM volatile (`tmpfs`, `memfd_create`) et en cloud déporté.
- **Sanctuaire de la Vie Humaine (`SacredLifeSentinel`)** : Veto mathématique strict en amont de toute exécution locale ou distante protégeant l'intégrité de la vie humaine.
- **Agent Cognitif Autonome Hermes 3 & Claude 3.7** : Décomposition récursive `<thinking>`, appels d'outils structurés `<tool_call>` et cycle ReAct complet.
- **Sandbox Root & Confinement Docker (`freeai-shadow`)** : Environnement éphémère Durci avec micro-init, arsenal cyber (`nmap`, `net-tools`, `tor`, `torsocks`) et repli automatique.
- **Passerelle Souveraine Tor Onion V3** : Contrôle distant incensurable, chiffré de bout en bout (Ed25519) et verrouillé au mode super-utilisateur (`lesaintAi`).
- **Persistance Dual-Cloud Résiliente** : Réplication miroir simultanée sur Neon PostgreSQL (GZIP-9) et sur le coffre Telegram Neural Vault (`/learn`).
- **Disaster Recovery & Auto-Clonage Telegram** : Sauvegarde instantanée de la totalité du code source en archive mémoire sur Telegram (`/telegram backup`).

---

## 🛠️ Démarrage Rapide

### Prérequis
- Linux (Ubuntu, Debian, Kali, Fedora, Arch)
- Python 3.10+
- Docker (optionnel, activé par défaut si présent)

### Lancement
```bash
# Installer les dépendances
pip install -r requirements.txt

# Lancer la console interactive FreeAI
python3 cli.py
```

### Commandes Essentielles
```bash
# Consulter l'état du système et de la RAM
/status

# Passer en mode super-utilisateur
/mode lesaintAi

# Lancer une mission autonome (Hermes-Claude)
/agent "Audite les ports d'écoute locaux et vérifie l'intégrité mémoire"

# Déployer la passerelle distante Tor Onion V3
/onion start

# Sauvegarder le kit de secours sur Telegram
/telegram backup
```

Pour la documentation complète de toutes les commandes et architectures, consultez le [GUIDE_UTILISATION_FREEAI.md](GUIDE_UTILISATION_FREEAI.md).

---

## 📜 Licence
Projet souverain développé sous licence MIT.
