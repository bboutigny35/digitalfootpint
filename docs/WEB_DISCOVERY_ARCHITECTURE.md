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

## Compatibilité et indexation

SQLite et PostgreSQL restent supportés par chaque migration. La recherche locale
commence par les index SQL existants. PostgreSQL Full Text Search ne sera ajouté
qu'avec une implémentation de repli SQLite testée. OpenSearch et le stockage objet
seront réévalués à partir de mesures réelles de volume et de latence.
