# Système de connecteurs

Le contrat de phase 2 expose métadonnées (identifiant/version/capacités), types
d'entrée, validation de configuration, santé, quotas et méthode asynchrone de scan.
Les adaptateurs appliquent des timeouts explicites ; le worker applique les quotas
partagés et le backoff persistant avec jitter. Chaque processus traite un scan à la
fois, tandis que le bail et le rate limiting en base coordonnent plusieurs workers.

Le contrat, le registre et un connecteur `mock` hermétique sont maintenant présents.
Le registre d'exécution n'ajoute le mock que si
`DIGITALFOOTPRINT_ENVIRONMENT=test` ; il reste absent des environnements de
développement et de production. Le runner persiste état, progression et résultats
dédupliqués. Le worker acquiert chaque scan par bail atomique, reprend les baux
expirés avec trois tentatives et applique un backoff persistant. Les limites
fournisseur partagées sont conservées en base.

Lors d'un `SIGTERM` ou `SIGINT`, le worker termine au plus la requête fournisseur
en cours, interrompt les attentes de rate limiting et remet le scan en file avec
le mécanisme de backoff persistant. Le bail reste la protection de secours si le
processus est arrêté de force ; il permet la reprise après expiration.

La corrélation `weighted-signals-v1` additionne des signaux documentés et conserve
les poids contributeurs. La seule égalité d'un pseudonyme vaut 0,20 et reste donc
incertaine. Chaque explication rappelle que le score n'est pas une preuve.

Les connecteurs réels initiaux sont GitHub et GitLab via leurs API officielles,
Wayback via le CDX Server documenté, et Brave Search via son API officielle.
Bing et HIBP resteront facultatifs selon clé et conditions. Sherlock et Maigret ne seront ajoutés qu'après revue
de licence, isolation en sous-processus sans shell et tests de comportement.

## SearXNG auto-hébergé

Le connecteur `searxng` utilise l'API JSON locale de SearXNG, activée dans
`deploy/searxng/settings.yml`. Son endpoint est limité à `127.0.0.1:8888` pour
l'installation native ou au nom Docker interne `searxng:8080` pour Compose ; les
endpoints arbitraires, ports personnalisés et redirections sont refusés. Le
connecteur envoie un POST, afin que la requête ne soit pas inscrite dans l'URL par
le proxy local. Les URL de résultats ne sont jamais ouvertes par ce connecteur.

SearXNG reçoit uniquement le nom complet et les pseudonymes, avec cinq requêtes
maximum par scan et cinq POST par minute globalement. Les e-mails, variantes,
domaines et mots-clés ne sont pas transmis. L'interface demande confirmation et
l'API rejette les scans SearXNG/Brave sans indicateur de consentement explicite.
SearXNG relaie ensuite la requête aux moteurs activés ; chacun peut appliquer ses
propres conditions, limites, protections anti-bot et durées de conservation. Les
CAPTCHA et blocages ne sont pas contournés. Le connecteur est non prêt tant qu'un
endpoint local n'est pas configuré.

L'image Compose est épinglée sur la version amont `2026.10.19-81371861f`. La
configuration active JSON et SafeSearch modéré, désactive le proxy d'images et ne
publie aucun port en mode Compose. En natif, le seul port hôte est lié à loopback.
Le limiteur SearXNG est désactivé car l'instance est privée ; le rate limiting de
DigitalFootprint s'applique, mais une publication réseau directe de SearXNG est
interdite par la configuration documentée.
SearXNG est un logiciel distinct sous licence AGPL-3.0-or-later ; son image et sa
licence restent séparées de la licence MIT de DigitalFootprint.

Références amont : [API de recherche](https://docs.searxng.org/dev/search_api.html),
[configuration des formats](https://docs.searxng.org/admin/settings/settings_search.html)
et [installation Docker](https://docs.searxng.org/admin/installation-docker.html).

Aucun connecteur ne contournera CAPTCHA, authentification, robots ou mesure anti-bot.
Les tests unitaires utilisent un transport HTTP simulé et ne touchent jamais
Internet. Le parcours Playwright lance l'API et un worker avec une base SQLite
temporaire, puis utilise exclusivement le connecteur `mock`.

Les fournisseurs du moniteur sensible utilisent un contrat distinct dans
`sensitive_monitor/connectors.py`. Un adaptateur déclare ses catégories, s'il
transmet une donnée hors de l'instance et s'il exige une confirmation. Un fournisseur
local ne reçoit qu'une empreinte HMAC et un libellé de source. Aucun adaptateur
externe sensible n'est actuellement activé.

## GitHub

Le connecteur `github` consulte uniquement l'API REST officielle et seulement le
profil public correspondant exactement à chacun des pseudonymes fournis, dans la
limite de dix pseudonymes par exécution. Il ne suit aucune redirection et construit
l'URL publique depuis le nom retourné au lieu de suivre une URL distante.

Avant chaque requête, le worker réserve atomiquement un créneau dans la table
`provider_throttles`. Cette limite est partagée entre processus, utilisateurs et
redémarrages. Pour GitHub, dix requêtes par minute au maximum sont autorisées. Si
les en-têtes officiels annoncent un quota restant nul, l'instant de réinitialisation
est persisté et aucune nouvelle requête n'est émise avant cette date.

Un jeton facultatif peut être fourni par `DIGITALFOOTPRINT_GITHUB_API_TOKEN`. Il
est envoyé dans l'en-tête `Authorization`, jamais dans l'URL ou les erreurs. Sans
jeton, GitHub autorise les consultations publiques mais applique un quota inférieur.
Les réponses `403` et `429` arrêtent le connecteur ; elles ne sont pas relancées
aveuglément. Les tests utilisent `MockTransport` et ne contactent pas Internet.

Le connecteur est enregistré dans le worker persistant et testé avec un transport
simulé. Les tests automatisés n'effectuent aucun appel réseau réel.

## GitLab

Le connecteur `gitlab` consulte exclusivement le point d'accès officiel public
`GET /users/:id_or_username/status`, documenté comme accessible sans
authentification. Il n'envoie que les pseudonymes fournis, sans nom ni adresse
électronique, limite chaque scan à dix pseudos distincts et ne conserve pas le
message de statut distant. Il n'utilise ni instance GitLab arbitraire ni URL de
redirection. Une réponse 404 signifie uniquement qu'aucun profil correspondant
n'a été exposé par ce point d'accès ; toute autre erreur fournisseur est
ramenée à un message générique.

Le worker réserve au plus dix requêtes par minute dans le rate limiter partagé
en base. C'est une limite locale conservatrice, et non une affirmation sur le
quota de GitLab.com : les instances GitLab peuvent appliquer des limites
configurables différentes. Un 403/429 arrête le connecteur et la file applique
ensuite son mécanisme de reprise avec backoff. Les tests utilisent exclusivement
`MockTransport`.

## Internet Archive / Wayback

Le connecteur `wayback` interroge l'API CDX officielle uniquement pour les
domaines et sites Web déjà saisis dans le profil. Les URL saisies sont réduites à
leur nom d'hôte ; les adresses IP et noms locaux sont refusés. Au plus dix domaines
et vingt captures HTTP 200 par domaine sont demandés. Les domaines imbriqués sont
regroupés, et les résultats distants
sont filtrés afin de ne retenir que le domaine demandé et ses sous-domaines.
Seules l'URL d'origine validée et la date sont conservées dans les résultats ; les
captures sont des pages archivées, pas la preuve que le contenu est encore publié
ou contrôlé par la personne. Aucun pseudonyme, nom ou e-mail n'est envoyé à
Internet Archive.

Le worker limite les appels CDX à cinq requêtes par minute via `provider_throttles`.
Les résultats sont limités par requête et les redirections HTTP sont désactivées.
Les tests simulés vérifient la construction de requête, la validation du domaine,
la minimisation et la réduction des erreurs, sans accès Internet.

## Brave Search

Le connecteur `brave` utilise exclusivement `GET /res/v1/web/search` de l'API
officielle. Il est facultatif et bloqué par défaut. Il exige à la fois un jeton
configuré dans le coffre chiffré (ou via la variable d'environnement documentée)
et l'approbation opérateur `DIGITALFOOTPRINT_BRAVE_CONTRACT_APPROVED=true`, qui ne
doit suivre qu'une revue juridique du plan et des droits de stockage. Il limite chaque scan à cinq
requêtes et dix résultats par requête et applique un plafond local de cinq
requêtes par minute. Le jeton est envoyé uniquement dans `X-Subscription-Token` ;
les redirections sont désactivées. Les erreurs distantes et corps HTTP ne sont
jamais copiés dans les exceptions.

Les requêtes contiennent seulement le nom complet et les pseudonymes exacts entre
guillemets. Les e-mails, variantes de nom et mots-clés du profil sont exclus. La
page de lancement explique la divulgation et demande une confirmation explicite
avant l'envoi à Brave. La notice Brave publiée indique une conservation possible
des journaux de requêtes jusqu'à 90 jours ; vérifier les conditions, le tarif et
la base juridique avant activation. Les tests reposent sur `MockTransport`, sans
accès Internet.

## Recherche globale

Le bouton **Recherche globale** sélectionne côté interface tous les connecteurs
activés et prêts dont les types d'identifiants sont présents dans le profil. Il
exige au moins un connecteur doté de la capacité `web_search`, afin de ne pas
confondre des consultations spécialisées GitHub/GitLab/Wayback avec une recherche
générale. Brave reste indisponible tant que l'approbation contractuelle et sa clé
ne sont pas configurées ; SearXNG
reste indisponible tant qu'une instance locale n'est pas définie. L'API rejette
les scans ou planifications sans configuration et exige une confirmation
explicite pour tout envoi à Brave ou SearXNG.

Cette orchestration n'implique pas que tous les sites du Web sont indexés. Elle
interroge les fournisseurs configurés, dans leurs limites et conditions propres.
Les nouvelles sources de recherche généraliste doivent être intégrées comme
connecteurs séparés après revue de leur API, contrat, confidentialité, quotas et
coût ; elles ne sont jamais activées implicitement.
