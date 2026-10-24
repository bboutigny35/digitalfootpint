# Architecture de découverte Web

Date : 24 octobre 2026. Statut : architecture incrémentale validée après l'audit.

## Principes

La découverte Web étend le monolithe modulaire existant. Elle réutilise FastAPI,
SQLAlchemy/Alembic, le worker à baux persistants, le registre de connecteurs et le
client HTTP protégé contre les SSRF. Redis, OpenSearch, MinIO et un navigateur
automatisé ne sont pas requis pour le premier périmètre.

Les valeurs par défaut restent compatibles avec SQLite : un seul consommateur,
une exploration séquentielle et des transactions courtes. PostgreSQL permet
ensuite plusieurs workers, sans modifier les contrats métier.

## Chaîne cible

```text
IdentityProfile
  -> SearchStrategyEngine
  -> DiscoveryConnector / PlatformConnector
  -> DiscoveredURL
  -> CrawlScheduler
  -> WebFetcher (SSRF + robots + limites)
  -> CrawlResult
  -> EvidenceAnalyzer
  -> IdentityCorrelation
  -> UserValidation
```

Chaque étape persiste son état minimal et sa provenance. Une absence de résultat
ne prouve jamais l'absence d'un compte ou d'une page.

## Stratégie de recherche

`SearchStrategyEngine` est un service pur : une même version de profil et un même
mode produisent le même plan. Chaque requête indique son texte, ses critères, sa
priorité, sa portée et si une corroboration est obligatoire.

- `quick` : index local et cache récent uniquement ; budget de 8 requêtes.
- `standard` : sources locales, connecteurs prioritaires et découverte ciblée ;
  budget de 16 requêtes et exclusion des recherches sur nom seul.
- `deep` : tous les connecteurs activés compatibles, découverte progressive et
  corrélation ; budget de 30 requêtes.

Les e-mails exacts sont limités à la portée locale. Le moteur ne les transmet pas
aux moteurs généralistes. Une requête sur le nom seul est marquée comme exigeant
une corroboration et n'apparaît qu'en mode approfondi.

L'API `GET /api/v1/profiles/{id}/search-strategy?mode=...` permet au propriétaire
de prévisualiser le plan. Cette prévisualisation ne lance aucun accès réseau et
ne crée aucune campagne.

## Modèles persistants prévus

Les migrations seront additives et réparties pour faciliter les retours arrière :

1. `0012` : enrichissement additif d'`IdentityProfile` avec anciens pseudonymes,
   téléphones, ville/région, profession, employeurs, profils confirmés,
   expressions exactes et exclusions ;
2. `0013` : `WebSource`, catalogue des plateformes et configuration autorisée ;
3. `0014` : `DiscoveredURL`, `CrawlJob`, `CrawlResult` et statistiques de campagne,
   avec déduplication par empreinte d'URL canonique et baux persistants ;
4. `0015` : `Evidence`, correspondances, corrélations et validations utilisateur.
5. `0016` : tâches de découverte par campagne/source, avec priorité, tentatives
   bornées et baux persistants.
6. `0017` : résultats normalisés de vérification des plateformes par campagne.

`Scan` reste la campagne existante et `Result` le résultat public compatible. Les
nouvelles entités les référencent ; elles ne les dupliquent pas.

## Invariants de sécurité

- Toute URL distante non fiable passe par le validateur SSRF existant avant la
  connexion et après chaque redirection.
- Le crawler n'exécute pas de JavaScript distant.
- Robots.txt, limites MIME/taille/profondeur/pages et quotas par domaine sont
  vérifiés avant téléchargement.
- Les secrets ne sont jamais inclus dans les plans, preuves ou journaux.
- Les données, validations et exclusions restent cloisonnées par propriétaire.
- Les pages complètes ne sont pas conservées par défaut ; texte utile, empreinte,
  dates et provenance suffisent au premier périmètre.

La mise en file `0014` refuse déjà les identifiants intégrés aux URL, les ports
hors 80/443 et les adresses IP littérales non publiques. Un nom DNS accepté à ce
stade devra encore être résolu et validé juste avant connexion : l'inscription en
file ne constitue jamais une autorisation réseau.

## Ordonnancement du crawl

Le planificateur persistant sélectionne d'abord la priorité numérique la plus
faible, puis l'ancienneté. L'acquisition atomique place la tâche en `running`,
incrémente son nombre de tentatives et lui attribue un bail de cinq minutes. Un
bail expiré peut être repris tant que la limite de trois tentatives n'est pas
atteinte.

Une erreur récupérable replace la tâche en `queued`. Le délai suit le
`Retry-After` lorsqu'il est fourni, sinon un recul exponentiel, avec jitter et un
plafond de 24 heures. Après la troisième tentative, la tâche devient `failed` et
les statistiques de campagne sont mises à jour. La pause d'une campagne ne
modifie que ses tâches en attente ; les tâches déjà acquises terminent leur bail.

Ce planificateur ne télécharge lui-même aucune ressource. Le fetcher séparé
applique robots.txt, quotas et validation SSRF après résolution DNS et à chaque
redirection avant de produire un `CrawlResult` minimisé.

Le fetcher HTTP consulte `robots.txt` avant la page, bloque en cas de refus et
échoue de manière récupérable si ce fichier est temporairement indisponible.
Chaque requête et redirection repasse par la résolution publique et la connexion
épinglée du client anti-SSRF. Un quota persistant partagé est réservé par
empreinte SHA-256 du domaine, sans conserver le nom de domaine dans la table de
limitation.

Les réponses robots sont limitées à 256 Kio et les pages à 2 Mio, y compris en
l'absence de `Content-Length`. Le flux est interrompu dès dépassement. Seuls le
HTML, XHTML et le texte brut sont acceptés pour une page ; le fetcher n'exécute
aucun script et ne charge aucune sous-ressource. Les réponses `429` transmettent
un `Retry-After` numérique plafonné à 24 heures au planificateur.

L'étape de traitement retire scripts, styles, modèles, SVG et espaces superflus,
puis plafonne le texte conservé à 100 000 caractères. Le corps téléchargé n'est
jamais enregistré : `CrawlResult` contient seulement le texte extrait, la taille,
l'empreinte SHA-256, le type MIME, l'URL finale et les dates de cache/provenance.
La durée de cache configurée sur la source est respectée.

Au plus 50 liens d'un document HTML sont proposés à la file. Seuls les liens
HTTP(S) du même hôte sont retenus ; la validation syntaxique, la profondeur
maximale et la déduplication canonique sont ensuite réappliquées. La finalisation,
les nouveaux liens et les statistiques sont validés dans une seule transaction,
uniquement si le worker possède encore le bail de la tâche.

Le processus `digitalfootprint-scan-worker` conserve la priorité historique des
scans, traite ensuite une tâche de découverte, puis une tâche de crawl. Les
limitations, erreurs serveur et indisponibilités de robots sont reprises avec le
backoff persistant ; les refus robots, destinations interdites, types MIME et
tailles invalides échouent immédiatement. Un arrêt gracieux remet la tâche en
file et un worker ayant perdu son bail ne peut ni la replanifier ni l'écrire. Les
journaux ne contiennent que l'identifiant de tâche et un code d'erreur contrôlé,
jamais l'URL ni le contenu téléchargé.

## Documents de découverte

Les sitemaps, index de sitemaps, flux RSS et Atom partagent un contrat de candidat
normalisé. Leur analyse est limitée à 512 Kio et utilise `defusedxml` ; DTD et
entités sont refusées. Un document fournit au plus 1 000 pages ou 50 sitemaps
imbriqués. Seules les URL HTTP(S) du domaine exact de la source, sans identifiants
ni port non standard, sont admises.

La mise en file exige une source administrative `active`, conserve son identifiant
comme provenance et réapplique la canonicalisation et la déduplication du crawler.
Le téléchargement passe par le client anti-SSRF et son quota persistant pour
chaque document et chaque redirection. Une redirection hors du domaine exact est
refusée avant l'envoi de la requête HTTP correspondante.

Le parcours d'un index est limité à deux niveaux, 20 documents et 1 000 pages au
total. Les contenus XML acceptés sont limités à 512 Kio et aux types MIME XML,
RSS ou Atom. Le service reste isolé de la planification : l'activation d'une
source dans l'API d'administration ne déclenche pas elle-même de téléchargement.

Chaque exécution planifiée est représentée par un `DiscoveryJob` lié à une
campagne, son propriétaire et une source. La contrainte unique campagne/source
évite les doublons. L'acquisition est atomique, respecte la priorité de la source
et utilise un bail de cinq minutes avec trois tentatives et backoff borné. Une
écriture provenant d'un worker dont le bail est expiré ou repris est ignorée.
À la fin réussie d'une campagne, au plus 20 sources `active` de type `sitemap` ou
`feed` sont sélectionnées par priorité, domaine puis identifiant. Les sources
`pending` et les méthodes non exécutables sont exclues. Les jobs sont créés dans
la même transaction que le passage du scan à l'état terminé ; cette étape ne
réalise aucun accès réseau et s'applique aussi aux campagnes récurrentes.
Le téléchargement s'effectue hors transaction de lecture, puis la création des
URL et tâches de crawl et la clôture du job sont validées atomiquement. Les
limitations et erreurs serveur sont reprises ; document invalide, redirection
hors domaine, destination interdite, taille ou type MIME refusé sont définitifs.
Les journaux exposent seulement l'identifiant, les compteurs et un code contrôlé.

Les résultats des connecteurs ne sont proposés au crawl que si leurs métadonnées
déclarent explicitement `crawl_results`. GitHub, GitLab, Brave, SearXNG et Wayback
activent cette capacité ; le connecteur simulé et tout futur connecteur restent
refusés par défaut. Chaque URL repasse par les contrôles syntaxiques et réseau de
la file. Un refus de crawl ne supprime pas le résultat minimisé et ne fait pas
échouer la campagne.

L'étude Common Crawl est consignée dans `docs/COMMON_CRAWL_EVALUATION.md`. Son
index public correspond aux captures d'URL connues, subit de fortes limitations
et nécessiterait une chaîne WARC supplémentaire. Aucun connecteur n'est donc
activé dans ce périmètre ; une future expérimentation devra être désactivée par
défaut et limitée aux domaines/sites déjà fournis par l'utilisateur.

## Compatibilité et indexation

SQLite et PostgreSQL restent supportés par chaque migration. La recherche locale
commence par les index SQL existants. PostgreSQL Full Text Search ne sera ajouté
qu'avec une implémentation de repli SQLite testée. OpenSearch et le stockage objet
seront réévalués à partir de mesures réelles de volume et de latence.
