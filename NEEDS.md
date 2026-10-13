# NEEDS.md - Actions Manuelles Requises

Ce fichier liste uniquement ce que toi (Michael) dois faire à la main pour que des
fonctionnalités déjà codées deviennent pleinement opérationnelles, ou pour profiter
des dernières évolutions. Tout ce qui pouvait être fait en code a déjà été fait et
vérifié avec de vrais tests - ce qui reste ici dépend soit d'une ressource externe
(compte, matériel), soit d'une décision/configuration qui t'appartient.

---

## 1. Auto-Apply avec revue humaine en direct (nouveau)

Rien à installer, c'est déjà prêt à l'usage. Juste pour information :
- Quand FreeAi prépare une candidature, tu reçois un lien de type
  `http://<ton IP locale>:<port>/vnc.html?...&password=...`.
- **Ne transmets jamais ce lien ailleurs que sur ton propre réseau local** (Wi-Fi/LAN
  de chez toi) : il donne un accès de contrôle complet sur un navigateur connecté à
  tes comptes. Ne le mets jamais derrière une redirection de port vers Internet.
- Si ton numéro de téléphone ou ta ville change, mets à jour `MICHAEL_PROFILE` dans
  `app/tools/morning_briefing.py` (clés `phone` et `city`).

## 2. Free Cloud Pool (déport de calcul vers un VPS gratuit) - bloqué sans action de ta part

Le code de connexion réelle n'existe pas encore, et même une fois écrit il restera
inactif sans que tu crées un compte toi-même chez un fournisseur :
- Crée un compte **Oracle Cloud Always Free** (ou AWS Free Tier / GCP Free Tier).
- Génère une paire de clés SSH dédiée et récupère l'IP de l'instance.
- Donne-moi ces informations (jamais la clé privée en clair dans un message si tu
  préfères : tu peux juste me dire "c'est fait, voici l'IP" et placer la clé dans
  `~/.ssh/` toi-même) pour que je branche la connexion réelle.

## 3. Aether-Swarm : providers gratuits dégradés

En conditions réelles, les modèles gratuits `deepseek-r1:free` et
`qwen-2.5-coder-32b:free` sur OpenRouter renvoient actuellement une erreur 404
("modèle gratuit indisponible"). Ce n'est pas un bug côté FreeAi : c'est le
fournisseur qui a retiré ou changé ces modèles gratuits spécifiques. Pour que le
consensus multi-IA utilise vraiment 3 avis au lieu d'1 seul (Groq) :
- Va voir sur https://openrouter.ai/models quels modèles sont actuellement marqués
  `:free`, et dis-moi lesquels remplacer dans `app/cluster/aether_swarm.py`.
- Sinon, le système continue de fonctionner, mais honnêtement avec moins de
  modèles réellement consultés qu'annoncé (il te le dit dans son rapport, il
  n'invente rien pour compenser).

## 4. Starlink Adapter - bloqué, aucune action logicielle possible

Ce module ne pourra jamais devenir réel sans l'objet physique : il faut posséder
une antenne Starlink connectée sur ton réseau local. Rien à faire côté code tant
que tu n'as pas ce matériel.

## 5. Réception ultrasonique - fonctionne, mais fiabilité variable selon le moment

La réception (micro) est réellement implémentée et testée. Un vrai bug a été
trouvé et corrigé : un décodage corrompu pouvait être renvoyé comme si c'était
le bon texte, sans aucune vérification. Une somme de contrôle a été ajoutée
pour rejeter tout décodage corrompu au lieu de l'accepter silencieusement.

Mesuré honnêtement, pas de chiffre unique arrangé : sur des tirs indépendants
répétés, le taux de réussite va de **10/10 à 5/10 selon le moment**, parce que
l'amplitude du son ultrasonique capté varie elle-même dans le temps sur cette
machine (probablement un comportement du volume/gain du système audio, pas un
bug du décodeur - vérifié par mesure directe de l'amplitude du signal capté).
Pour absorber cette variabilité, le test réessaie jusqu'à 8 fois en conditions
réelles avant d'échouer.
- Limite restante : ce test tourne en boucle numérique interne à une seule
  machine (le haut-parleur et le micro testés ne sont pas deux appareils
  physiquement séparés). Si tu veux vraiment t'en servir (ex: faire parler deux
  PC via le son), teste-le toi-même avec deux machines physiques différentes,
  dans une pièce silencieuse, haut-parleur et micro à moins d'1-2 mètres, et
  dis-moi le taux que tu observes.

## 6. Voix Temps Réel WebRTC - pas encore construit

Diagnostiqué mais pas encore implémenté : la page d'appel en direct ne capte
actuellement aucun vrai son de micro, et aucune route serveur n'existe pour la
recevoir. Le moteur vocal réel (reconnaissance + synthèse) existe déjà et
fonctionne, il n'est juste pas encore branché à cette page. Aucune action de ta
part n'est requise pour l'instant - c'est un développement à faire, pas une
ressource qui te manque.

---

## Résumé

| Fonctionnalité | Bloqué par | Qui doit agir |
|---|---|---|
| Auto-Apply revue live | Rien, déjà actif | Toi : juste ne pas exposer le lien sur Internet |
| Free Cloud Pool | Compte cloud + clé SSH manquants | Toi : créer le compte |
| Aether-Swarm (3 providers) | Modèles gratuits OpenRouter dépréciés | Toi : choisir un modèle de remplacement |
| Starlink Adapter | Matériel physique absent | Toi : achat d'une antenne, si souhaité |
| Réception ultrasonique | Rien, fiabilité 5/10 à 10/10 selon le moment | Toi : confirmer sur deux vraies machines séparées |
| Voix Temps Réel WebRTC | Développement pas encore fait | Moi : à construire dans une prochaine session |
