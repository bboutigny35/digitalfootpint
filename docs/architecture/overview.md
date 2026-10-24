# Architecture générale

## Proposition

DigitalFootprint adopte un monolithe modulaire : une API FastAPI, un frontend
React statique, une base SQLite ou PostgreSQL, et un processus worker distinct
utilisant la même couche métier. Ce choix réduit les prérequis d'une installation
personnelle tout en laissant les scans survivre au navigateur et aux redémarrages.

```text
Navigateur -> Nginx -> React / API FastAPI -> repositories -> SQLite/PostgreSQL
                               |                    ^
                               v                    |
                         file de scans persistée -> worker
                               |
                         connecteurs isolés -> API publiques
```

Le processus Web ne réalise jamais un scan long. Il crée une tâche persistée. Le
worker la réclame atomiquement, renouvelle un bail et écrit sa progression. Un
ordonnanceur léger crée les occurrences planifiées. Aucun Redis n'est requis au
socle ; PostgreSQL sera recommandé pour plusieurs workers.

## Modules

- `api` : transport HTTP, validation et dépendances d'autorisation.
- `models` / `repositories` : persistance portable, sans règle fournisseur.
- `services` : cas d'usage et transactions.
- `connectors` : contrat commun et adaptateurs réseau isolés.
- `workers` : acquisition, reprise, annulation et progression des tâches.
- `security` : authentification, secrets, SSRF, journalisation sûre.
- `reporting` : rendus et neutralisation des contenus non fiables.

Le frontend ne possède aucune règle d'autorisation : chaque ressource est filtrée
par `owner_id` côté serveur. L'interface sera française par défaut et toutes les
chaînes passeront par le catalogue i18n.

## Dépendances retenues (référence du 14 octobre 2026)

Backend : Python 3.11–3.13, FastAPI 0.143.0, SQLAlchemy 2.1.4, Alembic 1.19.2,
Pydantic Settings 2.15.0, argon2-cffi 25.1.0, psycopg 3.2.10 et Uvicorn 0.37.0.
Le client de test Starlette repose sur HTTPX2 2.13.1. Les versions exactes sont
figées dans `backend/pyproject.toml` pour rendre les validations reproductibles.

Frontend validé avec Node.js 20.19.2 : React 19.3, TypeScript 5.9.3, Vite 7.3.7,
Tailwind CSS 4.1.14, React Router 7.18.4 et Vitest 4.1.11. Ces versions respectent
leurs plages de compatibilité, sont figées dans le lockfile et passent l'audit npm.

## Décisions structurantes

1. Sessions opaques hachées en base : révocables et non lisibles par le client.
2. UUID applicatifs en `varchar(36)` : comportement identique SQLite/PostgreSQL.
3. JSON limité aux listes de critères et explications ; entités requêtées en tables.
4. Événements d'audit sans contenu sensible ; codes d'erreur plutôt que réponses brutes.
5. Connecteurs sans clé désactivés explicitement, jamais alimentés par des données fictives.
6. Score déterministe composé de signaux documentés ; il ne constitue jamais une preuve.
