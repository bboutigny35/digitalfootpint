# Audit de la découverte Web

Date de l'audit : 24 octobre 2026.

## Objet et portée

Cet audit confronte le dépôt existant à la chaîne cible suivante : profil
d'identité, stratégie de recherche, découverte, vérification de plateformes,
exploration contrôlée, extraction, corrélation, indexation et revue humaine. Il
porte également sur l'interface, la sécurité, les tests, les déploiements et
l'état Git. Il ne vaut ni revue juridique des fournisseurs ni audit de sécurité
indépendant.

## Synthèse exécutive

DigitalFootprint est une application existante et fonctionnelle, pas un projet à
réinitialiser. Son architecture est un monolithe modulaire : API FastAPI,
SQLAlchemy/Alembic, SQLite ou PostgreSQL, worker persistant en base et interface
React/Vite. Le socle d'authentification, l'isolation par propriétaire, les scans,
les résultats, les exports, l'administration, cinq connecteurs de production et
les deux modes de déploiement sont réutilisables.

Le moteur actuel est toutefois un agrégateur de résultats de connecteurs, et non
encore un moteur complet de découverte et de crawl. Il ne possède pas de registre
persistant de sources, de file d'URL, de crawler HTML respectant robots.txt, de
cache documentaire, de modèle de preuve ou de corrélation d'identité séparant
pertinence et confiance d'attribution. La bonne évolution consiste donc à étendre
le monolithe et son worker, sans introduire Redis, OpenSearch ou un second
frontend à ce stade.

## État du dépôt

### Architecture et technologies

- Backend : Python 3.11–3.13, FastAPI, Pydantic, SQLAlchemy 2 et Alembic.
- Frontend : React 19, TypeScript 5.9, Vite 7 et Tailwind CSS 4.
- Stockage : SQLite pour l'usage personnel et PostgreSQL 17 pour la concurrence.
- Traitement asynchrone : worker séparé avec file, baux, reprise et limitation de
  fréquence persistés en base ; aucun broker externe.
- Déploiement : images Docker multi-stage, Compose SQLite/PostgreSQL, Nginx et
  unités systemd Debian 13.
- CI : définitions GitHub Actions et GitLab CI, sans publication automatique.
- Version déclarée : `0.1.0.dev0` côté backend et `0.1.0-dev` côté frontend.

### État Git et versions

Le dépôt n'a aucun commit, aucune branche historique exploitable, aucun tag et
aucun remote documenté. Tous les fichiers du projet sont actuellement non suivis
sur la branche `master`. Il est donc impossible d'auditer l'évolution réelle,
d'attribuer les changements ou de démontrer une progression depuis `0.1.0`.
Créer un premier commit constitue une opération de gouvernance importante : il
figerait l'intégralité de l'état existant comme historique initial.

### Modèles et migrations existants

Onze migrations Alembic créent notamment les utilisateurs, sessions, profils,
scans, résultats, événements d'audit, planifications, quotas fournisseurs,
secrets et configurations de connecteurs, notifications, exports et demandes de
suppression. Un module séparé couvre les descripteurs sensibles, consentements,
contrôles, constatations et alertes.

Les modèles logiques cibles déjà couverts, parfois sous un nom plus général, sont
`IdentityProfile`, `SearchCampaign` (`Scan`) et une première forme de résultat
indexé (`Result`). Les modèles `SearchCriterion`, `WebSource`,
`PlatformCheckResult`, `DiscoveredURL`, `CrawlJob`, `CrawlResult`, `Evidence`,
`EvidenceMatch`, `IdentityCorrelation`, `UserValidation` et `CrawlStatistics`
n'existent pas comme entités distinctes.

## Fonctionnalités opérationnelles et réutilisables

### Identité, authentification et confidentialité

- Bootstrap d'un administrateur local, mots de passe Argon2id, sessions hachées,
  rotation, expiration, cookie HttpOnly et protection CSRF.
- Profils privés par propriétaire, avec prénom, nom, variantes, pseudonymes,
  e-mails, domaines, sites, profils sociaux, mots-clés et contexte.
- Validation d'e-mail et d'URL, normalisation Unicode/casse/espaces et
  déduplication des listes.
- Isolation multi-utilisateur testée sur les principales API.
- Coffre de jetons chiffré AES-256-GCM avec rotation de clés hors base.
- Rétention et purge du module sensible ; aucune valeur sensible brute conservée.

### Connecteurs et scans

- Contrat de connecteur typé et registre extensible.
- GitHub par API officielle, GitLab par endpoint public, Wayback/CDX limité aux
  domaines connus, Brave Search facultatif et SearXNG auto-hébergé.
- Consentement explicite pour les moteurs généralistes ; seules les données
  minimisées prévues sont transmises.
- Activation/désactivation administrative, état de préparation, dernier contrôle
  et erreurs agrégées.
- Déduplication d'URL canonique dans un scan et score de pertinence déterministe
  accompagné d'une explication.
- File persistante, acquisition atomique par bail, reprise après interruption,
  trois tentatives, backoff et limitation de fréquence partagée.
- Planifications quotidienne, hebdomadaire et mensuelle ; annulation d'un scan.

### Sécurité réseau

- Validation des schémas, ports, résolutions DNS et adresses avant connexion.
- Blocage loopback, réseaux privés, link-local et destinations non autorisées,
  avec règles bornées pour SearXNG local.
- Connexion épinglée à l'adresse validée, conservation de `Host` et SNI, retrait
  d'`Authorization` lors d'un changement d'origine et validation de chaque
  redirection.
- Tests hermétiques avec transports HTTP simulés ; aucun accès tiers requis par
  la suite automatisée.

### API et interface

- CRUD des profils, scans et résultats, recherche paginée avec filtres et tris,
  comparaison de scans et validation manuelle d'un résultat.
- Tableau de bord, exports CSV/JSON/XLSX/HTML/PDF, notifications internes,
  demandes de suppression et écran d'administration.
- Interface française/anglaise et composants déjà responsive dans les pages
  principales.
- Parcours E2E authentification, profil, scan simulé, résultat et export.

### Déploiement et exploitation

- Compose SQLite et PostgreSQL sans port de base publié, healthchecks,
  conteneurs non-root, capabilities supprimées et Nginx en lecture seule.
- Installateur, mise à jour, désinstallation, sauvegarde/restauration et unités
  systemd Debian 13.
- Sauvegardes SQLite/PostgreSQL, migrations et restauration synthétique déjà
  couvertes par tests ou validations documentées.

## Écarts fonctionnels

### Profil et stratégie de recherche

- Prénom et nom sont obligatoires ; le besoin cible autorise des profils reposant
  sur d'autres critères suffisamment discriminants.
- Téléphones, localisation structurée, profession, employeurs, anciens
  pseudonymes, expressions exactes, exclusions et profils confirmés ne disposent
  pas de champs dédiés.
- La normalisation téléphonique et les variantes bornées des noms composés ne
  sont pas implémentées.
- Il n'existe pas de `SearchStrategyEngine` produisant des requêtes explicites,
  priorisées, dédupliquées et bornées, ni de modes rapide/standard/approfondi.

### Catalogue de plateformes

- Le registre ne décrit que les cinq connecteurs implémentés ; il ne représente
  pas les plateformes non vérifiables ou non encore connectées.
- Les méthodes de vérification, priorités, restrictions, paramètres autorisés et
  statuts `PUBLIC_MATCH`, `POSSIBLE_MATCH`, `NO_PUBLIC_RESULT`, `USER_VERIFIED`,
  `NOT_VERIFIABLE`, `RATE_LIMITED`, `ACCESS_RESTRICTED`, `ERROR` ne sont pas
  modélisés.
- L'actuel `VerificationStatus` qualifie la revue d'un résultat
  (`confirmed/probable/uncertain/false_positive/ignored`) et ne doit pas être
  détourné pour représenter le résultat technique d'un contrôle de plateforme.

### Découverte, crawl et cache

- Aucun `SourceRegistry` persistant ni import contrôlé d'URL.
- Pas de connecteurs sitemaps ou RSS/Atom, ni de connecteur Common Crawl.
- Pas de file persistante au niveau URL, priorité par URL, profondeur, quota par
  domaine, pause/reprise ou circuit breaker par source.
- Pas de téléchargement HTML générique, robots.txt, limite MIME/taille,
  extraction de texte/liens, empreinte de contenu, détection de modification ou
  page supprimée.
- Pas de politique de fraîcheur documentaire permettant d'éviter un nouveau
  téléchargement.

### Preuves et corrélation

- `Result` mélange découverte, extrait, score et revue ; il n'existe pas de
  provenance détaillée ou de preuve immuable associée à chaque critère.
- Le score courant mesure une pertinence heuristique. Il n'existe pas de score
  distinct et explicable de confiance d'attribution.
- Pas de détection structurée d'homonymes, d'entités non personnelles, de
  contradictions ou de copies d'une même preuve.
- La confirmation/rejet existe sur un résultat, mais elle n'alimente pas encore
  un profil confirmé ou une exclusion réutilisable par utilisateur.

### Campagnes, supervision et interface

- Un scan peut être annulé, mais pas suspendu puis repris explicitement.
- La progression est globale ; les sources interrogées et résultats
  intermédiaires ne forment pas une chronologie de campagne détaillée.
- Les compteurs de crawl, file d'URL, réseau et stockage n'existent pas.
- La création de recherche n'est pas un assistant en cinq étapes. La page OSINT
  principale dépasse mille lignes et gagnerait à être découpée avant extension.
- Les tests de composants couvrent les principaux comportements, mais aucun audit
  automatisé WCAG 2.2 AA ni matrice de tailles d'écran n'est présent.

### Indexation et stockage

- La recherche actuelle est SQL classique ; aucun index PostgreSQL Full Text
  Search n'est défini.
- L'absence d'OpenSearch et de stockage objet est cohérente avec la volumétrie
  actuelle. Leur ajout immédiat créerait une complexité injustifiée.
- Les quotas de stockage, l'historique documentaire et l'expiration du cache Web
  ne sont pas implémentés.

## Problèmes et incohérences identifiés

1. L'absence totale d'historique Git est le principal risque de traçabilité et de
   régression avant une évolution de cette ampleur.
2. La version `0.1.0.dev0` ne reflète pas le périmètre, mais aucune donnée Git ne
   permet de justifier immédiatement une version stable 1.0.0.
3. `docs/development/progress.md` contient des validations historiques utiles,
   mais certaines tâches anciennes sont devenues incohérentes avec les
   validations DEB13-TEST plus récentes ; ce document doit devenir un journal
   daté plutôt qu'une source unique de vérité.
4. Les pages React métier sont volumineuses, en particulier l'espace OSINT, ce
   qui accroît le risque de régression lors de l'ajout d'un assistant multi-étapes.
5. Le registre de connecteurs est en mémoire et les métadonnées administratives
   persistées restent minimales (`enabled` uniquement).
6. La VM DEB13-TEST est actuellement arrêtée et ne peut pas démarrer tant que le
   réseau libvirt `default` reste inactif ; voir `docs/TEST_ENVIRONMENT.md`.

## Risques de régression

- Une migration directe des profils peut casser les formulaires, exports et
  connecteurs existants ; les nouveaux champs doivent être facultatifs et ajoutés
  par migration additive.
- Modifier `Result` ou ses statuts peut casser comparaison, rapports,
  notifications et demandes de suppression. De nouvelles tables de preuve et de
  contrôle de plateforme doivent référencer `Result` sans remplacer ses contrats
  actuels dans un premier temps.
- Le parallélisme de crawl peut compromettre SQLite. La valeur par défaut doit
  rester séquentielle et les acquisitions atomiques doivent fonctionner sur les
  deux bases.
- Tout nouveau chemin réseau peut rouvrir SSRF, rebinding DNS ou fuite de secrets.
  Le client sortant existant doit être le point de passage obligatoire, y compris
  pour robots.txt et chaque redirection.
- Les recherches générales peuvent divulguer des critères et générer des coûts ;
  les consentements et la minimisation actuels doivent être conservés.
- Une conservation de pages complètes augmenterait les risques juridiques et de
  stockage ; conserver prioritairement texte pertinent, empreintes et provenance.

## Architecture d'évolution proposée

### Lot 1 — fondations additives

1. Étendre `IdentityProfile` avec des champs facultatifs structurés et une
   normalisation testée, sans modifier les champs actuels.
2. Ajouter un `SearchStrategyEngine` pur et déterministe avec un budget de
   combinaisons et trois modes.
3. Créer un catalogue de plateformes persistant, séparé des résultats de revue,
   et y déclarer explicitement les plateformes non vérifiables.
4. Créer `WebSource`, `DiscoveredURL` et `CrawlJob` par migration additive.

### Lot 2 — découverte et exploration contrôlée

1. Normaliser les sorties SearXNG, Brave et Wayback en `DiscoveredURL`.
2. Ajouter sitemaps et RSS/Atom avant Common Crawl, car ils sont plus simples,
   bornés et faciles à tester hors réseau.
3. Étendre le worker existant à une file URL séquentielle avec quotas globaux et
   par domaine, pause/reprise, `Retry-After`, backoff et circuit breaker.
4. Implémenter un fetcher HTML sans JavaScript, fondé sur le validateur SSRF
   existant, respectant robots.txt et des limites MIME/taille strictes.

### Lot 3 — preuves et corrélation

1. Ajouter `CrawlResult`, `Evidence`, `EvidenceMatch`,
   `IdentityCorrelation` et `UserValidation` sans dupliquer `Result`.
2. Séparer score de pertinence et confiance d'attribution, avec facteurs et
   contradictions lisibles.
3. Réutiliser les validations du seul propriétaire pour profils confirmés,
   homonymes et exclusions.

### Lot 4 — interface et exploitation

1. Découper `OsintWorkspacePage` en composants testables puis introduire
   l'assistant en cinq étapes.
2. Ajouter la chronologie de campagne, suspension/reprise et compteurs de crawl.
3. Ajouter tests responsive et accessibilité automatisée, complétés par une
   revue clavier/lecteur d'écran manuelle.
4. Finaliser documentation, procédures de release et validation des deux modes
   de déploiement sur DEB13-TEST.

## Décisions structurantes nécessitant validation

1. **Historique initial** : la création d'un premier commit englobant l'état
   audité a été autorisée le 24 octobre 2026, après revue des fichiers et recherche
   de secrets. Aucun tag ni push distant n'est autorisé.
2. **Réseau de DEB13-TEST** : le réseau et la VM ont été démarrés par
   l'utilisateur ; l'environnement invité a ensuite été vérifié sans modification
   globale de libvirt par l'agent.
3. **Politique juridique** : valider les catégories de sources, durées de
   conservation et conditions contractuelles avant de nouveaux fournisseurs
   externes réels.
4. **Périmètre 1.0** : confirmer si la première version stable exige toute la
   chaîne de crawl/corrélation ou un sous-ensemble explicitement documenté.

## Versioning recommandé

Conserver `0.1.0.dev0` pendant les migrations de fondation, faute d'historique
publié. Après création d'un historique initial et stabilisation des contrats API,
passer à `1.0.0-beta.1`, puis `1.0.0-rc.1` après validation complète sur SQLite,
PostgreSQL, Compose et Debian 13. `1.0.0` doit rester réservé à un périmètre public
documenté, migrable et couvert par la procédure de release.

## Vérifications exécutées le 24 octobre 2026

- Suite backend complète : réussie ; un test PostgreSQL optionnel ignoré.
- Ruff sur `app` et `tests` : réussi.
- Mypy strict sur 73 fichiers source : réussi.
- Vitest : 24 tests sur 24 réussis dans 9 fichiers.
- Build TypeScript/Vite : réussi.
- ESLint et contrôle Prettier : réussis.
- Aucun appel réseau tiers n'a été effectué par ces tests.
- DEB13-TEST : identité, Debian 13.7, ressources, réseau, accès HTTPS, versions,
  services et sondes locales inspectés ; Web, worker, Nginx, Docker et SearXNG
  actifs, application et SearXNG en HTTP 200.

## Critères de sortie de la phase A

L'état actuel, les composants réutilisables, les écarts, les risques, le plan et
les arbitrages sont désormais documentés. L'historique initial a été autorisé et
DEB13-TEST est disponible pour les prochaines validations.
