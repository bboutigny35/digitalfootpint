# Développement

Créer un environnement virtuel dans `backend/.venv`, installer `.[dev]`, puis
exécuter `pytest`, `ruff check .` et `mypy app`. Les tests sont hermétiques : toute
nouvelle intégration réseau doit injecter un transport simulé. Créer une migration
Alembic pour chaque changement de modèle et vérifier `upgrade`, `downgrade`, puis
`upgrade` sur SQLite et PostgreSQL.

## Intégration continue

GitHub Actions utilise `.github/workflows/ci.yml` et GitLab utilise
`.gitlab-ci.yml`. Les deux pipelines exécutent les contrôles backend et frontend,
les migrations SQLite, l’audit npm, les builds Docker et un démarrage Compose.
Le parcours Playwright démarre une base SQLite temporaire, applique toutes les
migrations et contrôle le bootstrap, la session, la création d’identité, le
worker, un scan simulé, la validation du résultat et le contenu d’un export CSV
ainsi qu'une véritable sauvegarde SQLite gzip, sans appeler de fournisseur
externe. Les PDF documentaires sont générés depuis Markdown. Aucune image ni
version n’est publiée automatiquement.

Avant de pousser, reproduire les contrôles principaux :

```bash
cd backend
.venv/bin/python -m ruff check app tests
.venv/bin/python -m mypy app
.venv/bin/python -m pytest --cov=app
.venv/bin/python -m pip_audit --strict .

cd ../frontend
npm run format:check
npm run lint
npm run typecheck
npm test -- --run
npx playwright install chromium
npm run test:e2e
npm audit --audit-level=high
npm run build

cd ..
./scripts/generate-docs-pdf.sh
```

Les deux PDF sont écrits dans `reports/documentation/` et restent des artefacts
générés : seules leurs sources Markdown sont versionnées. Les pipelines conservent
les PDF pendant sept jours pour permettre leur contrôle.
