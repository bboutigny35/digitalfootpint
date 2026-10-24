# Journal des modifications

## Non publié

- Planification de recherche déterministe avec modes rapide, standard et
  approfondi, budgets bornés et prévisualisation privée par profil.
- Profils enrichis avec anciens pseudonymes, téléphones, localisation,
  profession, employeurs, profils confirmés, expressions exactes et exclusions ;
  migration additive `0012` compatible SQLite/PostgreSQL.
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
