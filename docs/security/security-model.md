# Modèle de sécurité

## Frontières et menaces

Le navigateur, les résultats distants et toutes les URL collectées sont non fiables.
La base et l'hôte auto-hébergé sont administrés par l'utilisateur. Les principales
menaces sont l'accès horizontal, le vol de session, CSRF, SSRF/rebinding DNS,
injections, contenus actifs dans les rapports et fuite de secrets par les logs.

## Mesures

- Mot de passe Argon2id (64 Mio, 3 itérations, parallélisme 4).
- Session aléatoire 384 bits ; seuls les HMAC-SHA-256 sont conservés en base.
- Cookie HttpOnly, SameSite=Lax, `Secure` obligatoire derrière HTTPS ; mutations
  protégées par un jeton CSRF distinct.
- Filtrage serveur systématique sur le propriétaire et erreurs 404 non révélatrices.
- SQLAlchemy paramètre les requêtes ; Pydantic borne tailles et types.
- Limiteur de connexion local au processus en phase 1. Une politique persistante
  multi-processus reste à implémenter avant production distribuée.
- Le validateur SSRF rejette loopback, privé, link-local, CGNAT, multicast, non
  spécifié et métadonnées cloud après chaque résolution et redirection. Tous les
  résultats DNS doivent être publics, les ports sont bornés à 80/443 et les
  en-têtes d'autorisation sont retirés lors d'un changement d'origine. Le client
  se connecte à l'adresse IP effectivement validée et conserve le nom original
  pour l'en-tête `Host` et la vérification SNI/TLS. Il réapplique cette politique
  à chaque redirection et ferme la connexion après la réponse pour éviter sa
  réutilisation entre deux noms partageant une IP. Cela ferme la fenêtre de
  rebinding DNS.
- L'endpoint SearXNG est un paramètre administrateur restreint à l'origine Docker
  dédiée ou à `127.0.0.1:8888`; aucun endpoint fourni par l'utilisateur ou une
  source distante n'est utilisé. Les redirections sont désactivées. En complément,
  l'instance de recherche n'est pas publiée sur le réseau et seuls des POST
  minimisés sont envoyés après confirmation explicite, vérifiée également par API.
- Les exports neutralisent `=`, `+`, `-`, `@`, tabulation et retour chariot en
  cellule, échappent HTML et n'intègrent aucune ressource distante dans le PDF.

## Secrets et données

Les clés fournisseur administrables sont chiffrées au repos par AES-256-GCM avec
nonce aléatoire, données associées au connecteur et clé maître versionnée fournie
par fichier protégé ou variable d'environnement. Elles ne sont jamais retournées
par l'API. La rotation déchiffre avec l'ancienne version et rechiffre avec la clé
active dans une transaction. Les logs utilisent des identifiants techniques,
jamais mots de passe, jetons, clés ou valeurs complètes des identités. Les sauvegardes
doivent être chiffrées hors application et testées. DigitalFootprint ne conserve
aucun identifiant ou mot de passe provenant de fuite.

Limitations actuelles : le limiteur de tentatives de connexion est local au
processus et devra devenir partagé avant un déploiement multi-worker. Le worker
recharge ses secrets avant chaque scan. Le socle n'est pas encore déclaré prêt
pour une exposition réseau directe. Les moteurs amont de SearXNG peuvent
enregistrer les requêtes, et cette rétention varie selon le moteur.

## Menaces propres aux données sensibles

- **Fuite par logs/erreurs** : aucune valeur brute n'est passée au logger ; les
  erreurs fournisseur sont réduites à des codes stables.
- **Recherche abusive** : NIR, PAN et pièce sont séparés des connecteurs OSINT ;
  chaque ressource est filtrée par propriétaire et toute mutation exige CSRF.
- **Attaque par dictionnaire** : les comparaisons reposent sur un HMAC secret avec
  séparation de domaine, jamais sur un hash public non salé.
- **Exfiltration fournisseur** : le contrat déclare transmission et catégories ;
  les fournisseurs externes nécessiteront un consentement explicite non révoqué.
- **Données bancaires** : PAN complet, CVV/CVC et PIN sont refusés et ne figurent
  dans aucun modèle. Un masque de carte ne contient que réseau et quatre chiffres.
- **Fausse assurance** : toute interface et tout rapport doivent rappeler que
  l'absence d'alerte n'est pas une preuve d'absence de compromission.

Le NIR est particulièrement encadré juridiquement. Le module initial effectue
uniquement une validation locale éphémère et ne prétend pas fournir une base légale
pour sa collecte ou sa recherche.
