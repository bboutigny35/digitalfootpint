# Journal des modifications

## Non publié

- Planification de recherche déterministe avec modes rapide, standard et
  approfondi, budgets bornés et prévisualisation privée par profil.
- Profils enrichis avec anciens pseudonymes, téléphones, localisation,
  profession, employeurs, profils confirmés, expressions exactes et exclusions ;
  migration additive `0012` compatible SQLite/PostgreSQL.
- Catalogue persistant des plateformes, statuts de vérification explicites et
  registre administratif des sources Web via la migration `0013`.
- File persistante de découverte et crawl : URL canoniques dédupliquées, tâches à
  baux, résultats minimisés, cache et statistiques via la migration `0014`.
- Planificateur de crawl persistant avec priorité, acquisition atomique, baux de
  cinq minutes, trois tentatives, reprise bornée et contrôle privé pause/reprise.
- Fetcher Web isolé avec robots.txt, quota persistant par domaine pseudonymisé,
  téléchargement borné, filtrage MIME et validation SSRF de chaque redirection.
- Extraction HTML minimisée sans corps brut, découverte bornée des liens de même
  hôte et persistance atomique avec contrôle du bail et provenance de la source.
- Raccordement au worker existant avec priorité aux scans, arrêt gracieux,
  distinction des erreurs permanentes/récupérables et journaux sans URL.
- Normalisation hermétique des sitemaps, RSS et Atom avec `defusedxml`, limites
  strictes, filtrage au domaine source et mise en file avec provenance.
- Téléchargement anti-SSRF des documents de découverte avec quota persistant,
  MIME/taille bornés et parcours d'index limité à deux niveaux et 20 documents.
- Migration `0016` et file de découverte par campagne/source avec acquisition
  atomique, priorité, baux, reprise bornée et protection contre les workers périmés.
- Consommation des tâches de découverte par le worker avant le crawl, avec
  finalisation atomique, erreurs temporaires ou définitives et journaux minimisés.
- Sélection automatique, déterministe et plafonnée des sources sitemap/feed
  actives lors de la finalisation des campagnes manuelles ou récurrentes.
- Alimentation du crawl par les seuls connecteurs qui l'autorisent explicitement,
  avec nouvelle validation des URL et refus sans échec du résultat public.
- Évaluation documentée de Common Crawl et report motivé de son intégration en
  raison de l'inadéquation à la recherche d'identité et des contraintes CDX/WARC.
- Migration `0017`, finalisation atomique des contrôles de plateformes réellement
  évaluées et API privée par campagne avec statuts normalisés et explicites.
- Connecteur Bluesky officiel par résolution exacte de handle, limité, sans clé,
  sans redirection et rattaché au catalogue par la migration réversible `0018`.
- Preuves avec provenance, correspondances minimisées, confiance d'attribution
  distincte et validations privées via la migration `0015`.
- Connecteur généraliste SearXNG auto-hébergé, endpoints locaux bornés, requêtes
  POST minimisées, consentement explicite frontend/API et déploiement Compose/Debian.
- Initialisation du dépôt et documentation d'architecture.
- Socle FastAPI/SQLAlchemy/Alembic.
- Authentification locale par session et profils d'identité isolés par utilisateur.
- Connecteur GitLab public et connecteur Internet Archive/Wayback CDX limités aux
  pseudonymes et domaines renseignés dans le profil.
- Connecteur Brave Search API facultatif, limité aux noms et pseudonymes, avec
  confirmation explicite, clé dans le coffre chiffré et quotas persistants.
- Correction du downgrade PostgreSQL initial : suppression explicite des types
  ENUM et ajout d'un cycle complet de migrations PostgreSQL dans les deux CI.
- Ajout de `postgresql-client` à l'image runtime pour rendre les sauvegardes et
  restaurations PostgreSQL administrables compatibles avec Docker Compose.
- Arrêt gracieux du worker : interruption du rate limiter et replanification du
  scan au signal d'arrêt.
