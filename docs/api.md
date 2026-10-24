# API

## Prévisualisation de la stratégie de recherche

`GET /api/v1/profiles/{profile_id}/search-strategy?mode=standard` retourne le
plan déterministe du propriétaire sans lancer de scan ni effectuer d'accès
réseau. Les modes acceptés sont `quick`, `standard` et `deep`. Chaque requête
indique sa priorité, ses critères, sa portée (`local`, `specialized` ou `general`)
et si une corroboration est requise. Les e-mails exacts ne reçoivent jamais la
portée `general`.

L'API est versionnée sous `/api/v1`. OpenAPI et Swagger UI sont servis sur `/docs`.

Les profils acceptent aussi les anciens pseudonymes, téléphones, ville/région,
profession, employeurs, profils confirmés, expressions exactes et exclusions.
Les listes textuelles sont normalisées en Unicode NFKC, avec espaces homogènes
et déduplication insensible à la casse. Les téléphones internationaux commençant
par `+` ou `00` sont conservés sous une forme `+` suivie de chiffres ; un numéro
sans indicatif reste numérique afin de ne pas inventer un pays.

- `GET /dashboard` : agrégats complets du propriétaire et évolution quotidienne
  des mentions sur les 30 derniers jours.
- `POST /auth/bootstrap` : premier compte administrateur uniquement.
- `POST /auth/login`, `POST /auth/logout`, `GET /auth/me`.
- `GET /auth/csrf` : rotation et restitution non mise en cache du jeton CSRF
  pour une session cookie existante.
- `POST /auth/refresh` : rotation de la session et du jeton CSRF.
- `POST /auth/users` : création d'un compte par un administrateur.
- `GET|POST /profiles`, `GET|PUT|DELETE /profiles/{id}`.
- `GET|POST /scans`, `GET /scans/{id}`, `POST /scans/{id}/cancel`.
- `GET /results` et `PATCH /results/{id}/verification`.
- `GET /results/search` : recherche paginée avec filtres par texte, connecteur,
  domaine, statut et dates, plus tri contrôlé par date, titre, score ou domaine.
- `/sensitive-monitor/descriptors` : descripteurs masqués, cartes limitées au
  réseau et aux quatre derniers chiffres, suppression par propriétaire.
- `/sensitive-monitor/validate` : validation locale éphémère du NIR et des
  pièces d'identité ; la valeur est transmise uniquement dans le corps HTTPS.
- `/sensitive-monitor/checks/local` et `/sensitive-monitor/checks` : contrôle
  local autorisé et historique sans valeur sensible brute.
- `GET /sensitive-monitor/findings` et `GET /sensitive-monitor/alerts` :
  constatations et alertes limitées au propriétaire authentifié.
- `POST /sensitive-monitor/alerts/{id}/acknowledge` : prise en compte auditée,
  protégée par CSRF et sans donnée sensible dans l'événement d'audit.
- `GET /health/live` : vivacité sans dépendance externe.

### Registres administratifs de découverte

- `GET /admin/platform-catalog` : plateformes, méthodes réelles, statut par
  défaut, priorité, limitations et connecteur éventuel.
- `GET|POST /admin/web-sources` : consultation et ajout manuel d'une source ; une
  source nouvelle reste `pending` et aucun accès réseau n'est lancé.
- `PATCH /admin/web-sources/{id}` : état, priorité, cache, fréquence et
  restrictions. Les mutations exigent administrateur et CSRF.

Les mutations authentifiées exigent le cookie `df_session` et l'en-tête
`X-CSRF-Token` retourné à la connexion. Le token CSRF doit rester en mémoire côté
frontend, jamais dans `localStorage`.

Créer un scan persiste une tâche `queued` destinée au worker ; la requête HTTP
n'exécute pas le scan. L'API publique ne permet pas d'insérer des résultats.
Pour inclure `brave` ou `searxng`, `POST /api/v1/scans` exige
`external_search_consent: true`. Cette propriété exprime la confirmation explicite
de l'utilisateur ; l'action est auditée sans enregistrer les termes. Les
planifications avec ces fournisseurs exigent le même indicateur à la création.

## Comparaison de scans

`GET /api/v1/scans/compare/results` accepte `baseline_scan_id` et
`current_scan_id`. Les deux scans doivent être terminés, appartenir à
l'utilisateur authentifié et porter sur le même profil. La réponse contient les
compteurs, le détail des URL et une note méthodologique. L'absence dans un scan
ne produit jamais automatiquement un état « supprimé » ou « inaccessible ».

## Demandes de suppression

- `GET|POST /api/v1/removal-requests` liste ou crée les dossiers du propriétaire.
- `PATCH|DELETE /api/v1/removal-requests/{id}` met à jour ou supprime un dossier.
- `GET /api/v1/removal-requests/{id}/letter` prépare un modèle de courrier RGPD.

Les mutations exigent un jeton CSRF. La génération d’un courrier n’entraîne aucun
envoi, appel réseau ou changement automatique du statut du dossier.

## Notifications internes

- `GET /api/v1/notifications` retourne les 100 dernières alertes du propriétaire.
- `POST /api/v1/notifications/{id}/read` marque une alerte comme lue.
- `GET|PATCH /api/v1/notifications/preferences` consulte ou modifie l’activation
  des alertes de nouvelles mentions.

Une alerte est créée après un scan uniquement lorsqu’un scan antérieur comparable
existe et que de nouvelles URL sont détectées. Son texte ne contient ni identité,
ni URL de résultat, ni donnée sensible.

## Administration

- `GET /api/v1/admin/overview` retourne la version, le type de base, le mode des
  cookies et des booléens de configuration, sans valeur de secret.
- `GET /api/v1/admin/audit-events` fournit un journal paginé réservé aux
  administrateurs. Les détails sont filtrés par liste blanche.

Ces routes renvoient `403` aux comptes non administrateurs. Elles ne permettent
pas de lire une URL de base, un jeton fournisseur ou un fichier de sauvegarde.
