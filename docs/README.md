# FreeAI Cyber Arsenal

## Description
`freeai_cyber.py` et `freeai_cyber.sh` permettent d'exécuter des outils Kali Linux de manière interactive ou non-interactive. Ce projet utilise `KaliToolRegistry` pour détecter et exécuter des outils locaux en toute sécurité.

---

## Prérequis
- **Système d'exploitation** : Kali Linux (recommandé) ou tout système avec les outils Kali installés.
- **Python 3** : Installé et disponible dans le `PATH`.
- **Outils Kali** : Les outils doivent être installés et accessibles via `PATH` (ex: `sqlmap`, `ffuf`, etc.).

---

## Installation des Outils Kali
Pour exécuter `freeai_cyber.py`, assurez-vous que les outils Kali sont installés. Voici quelques commandes pour installer des outils courants :

```bash
sudo apt update
sudo apt install sqlmap ffuf nikto tshark radare2 binwalk hydra hashcat aircrack-ng
```

---

## Utilisation

### Mode Interactif
Exécutez le script en mode interactif pour sélectionner et configurer des outils manuellement :

```bash
./freeai_cyber.sh -i
```

ou

```bash
python3 freeai_cyber.py --interactive
```

- **Étapes** :
  1. Sélectionnez un outil disponible.
  2. Entrez les arguments requis pour l'outil.
  3. Exécutez la commande et visualisez les résultats.

---

### Mode Non-Interactif
Exécutez une commande Kali directement avec des arguments JSON :

```bash
./freeai_cyber.sh -t sqlmap -a '{"target_url": "http://example.com", "extra_flags": "--dbs"}'
```

ou

```bash
python3 freeai_cyber.py --tool sqlmap --arguments '{"target_url": "http://example.com", "extra_flags": "--dbs"}'
```

---

## Exemples d'Utilisation

### Exemple 1 : Scanner SQL avec `sqlmap`
```bash
python3 freeai_cyber.py --tool sqlmap --arguments '{"target_url": "http://example.com/login.php?id=1", "extra_flags": "--batch --level=5 --risk=3"}'
```

### Exemple 2 : Fuzzing Web avec `ffuf`
```bash
python3 freeai_cyber.py --tool ffuf --arguments '{"url": "http://example.com/FUZZ", "wordlist": "/usr/share/wordlists/dirb/common.txt"}'
```

---

## Cas d'Usage Typiques
- **Audit de Sécurité** : Utilisez `nikto` ou `sqlmap` pour scanner des vulnérabilités.
- **Analyse de Réseau** : Utilisez `tshark` ou `aircrack-ng` pour capturer et analyser des paquets.
- **Reverse Engineering** : Utilisez `radare2` ou `binwalk` pour analyser des binaires.

---

## Erreurs Courantes
- **Outil Non Disponible** : Assurez-vous que l'outil est installé et accessible via `PATH`.
- **Arguments Invalides** : Vérifiez la syntaxe des arguments JSON.
- **Permissions** : Exécutez le script avec les droits nécessaires (`sudo` si requis).

---

## Contribuer
Les contributions sont les bienvenues ! Pour ajouter un nouvel outil :
1. Ajoutez-le au catalogue `KALI_TOOL_CATALOG` dans `kali_registry.py`.
2. Mettez à jour les schémas et les flags par défaut.
3. Ajoutez des tests pour le nouvel outil dans `test_freeai_cyber.py`.