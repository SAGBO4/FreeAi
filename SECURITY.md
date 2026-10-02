# Politique de Sécurité - FreeAI 🛡️

La sécurité, la souveraineté et l'éthique sont les fondations inaliénables de **FreeAI**. Ce document décrit notre politique de sécurité, les versions supportées et la procédure pour signaler une vulnérabilité.

---

## 🔒 Versions Prises en Charge

| Version / Branche | Prise en charge active | Correctifs de sécurité critiques |
| :--- | :--- | :--- |
| `main` | ✔ Oui | ✔ Immédiat |
| `dev` | ✔ Oui | ✔ En continu |
| Versions antérieures | ❌ Non | N/A |

---

## 🚨 Signaler une Vulnérabilité

Si vous identifiez une vulnérabilité de sécurité ou un moyen de contourner les gardes-fous du système, nous vous remercions de **ne pas ouvrir de ticket public (Issue GitHub)**.

### Procédure de divulgation responsable :
1. Envoyez un rapport détaillé directement à l'auteur principal :
   - **Contact GitHub** : [@SAGBO4](https://github.com/SAGBO4)
   - **Sujet** : `[VULNERABILITE-FREEAI] <Description succincte>`
2. Veuillez inclure dans votre rapport :
   - La description de la vulnérabilité et de son impact potentiel.
   - Les étapes précises pour reproduire le problème (PoC ou script de test).
   - Les composants impactés (`SacredLifeSentinel`, `ShadowDockerExecutor`, `TelegramVault`, etc.).
3. Une réponse d'accusé de réception vous sera adressée sous 24 à 48 heures avec un plan de remédiation.

---

## 🛡️ Architecture de Protection Native de FreeAI

FreeAI intègre nativement plusieurs cercles de défense hermétiques :

1. **Sacred Life Sentinel** :
   - Filtre heuristique et sémantique en amont interdisant toute instruction pouvant nuire à la vie humaine, aux systèmes de santé, aux réseaux énergétiques ou d'urgence.
2. **Confinement `freeai-shadow`** :
   - Isolation stricte des commandes système via conteneurs Docker éphémères rootless/root avec limitations de bande passante et de montage.
3. **Mode NÉANT** :
   - Éradication systématique de tout résidu persistant sur les disques physiques (SSD/HDD), neutralisant les attaques par récupération forensique locale.
4. **Passerelle Tor Onion V3** :
   - Chiffrement asymétrique de bout en bout (Ed25519) protégeant les flux distants contre les attaques de l'homme du milieu (MitM) et l'inspection de paquets.
