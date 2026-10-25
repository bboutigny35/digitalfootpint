# Tests de la découverte Web

Les tests automatisés n'accèdent pas au réseau. Les connecteurs, robots.txt,
redirections, sitemaps, flux et pages utilisent des transports HTTP simulés. Un
test nécessitant Internet est une régression de la politique du dépôt.

## Couverture attendue

- stratégie déterministe, budgets, déduplication et protection des e-mails ;
- normalisation/canonicalisation des URL et validation SSRF de chaque résolution
  et redirection, y compris DNS rebinding ;
- robots.txt, quotas, `Retry-After`, recul, taille, MIME et cache ;
- acquisition atomique, baux, reprise, trois tentatives et arrêt gracieux ;
- XML durci, sitemaps imbriqués, RSS/Atom, domaines et profondeurs bornés ;
- minimisation du contenu, provenance, corrélation, ambiguïtés et validations
  privées ;
- propriété des ressources, rôle administrateur, CSRF et absence de secrets ;
- migrations en montée/descente/remontée sur SQLite et PostgreSQL ;
- parcours Chromium synthétique desktop, mobile et tablette.

## Commandes principales

```bash
cd backend
.venv/bin/pytest -q
.venv/bin/ruff check app tests
.venv/bin/mypy app

cd ../frontend
npm test -- --run
npm run typecheck
npm run lint
npm run format:check
npm run build
npm run test:e2e
```

Les audits de dépendances, cycles PostgreSQL et builds Compose sont décrits dans
[`development/contributing.md`](development/contributing.md). Les tests
PostgreSQL opt-in doivent utiliser un cluster éphémère local et aucune écoute
réseau publique.

## Validation manuelle contrôlée

Sur `DEB13-TEST`, utiliser uniquement des profils et valeurs synthétiques sauf
autorisation explicite différente. Créer une sauvegarde avant déploiement,
contrôler le SHA-256 de l'artefact, la révision Alembic, les unités, le nombre de
redémarrages du worker et les healthchecks loopback. Ne conserver dans le compte
rendu ni URL individuelle, ni e-mail, ni secret, ni résultat OSINT.

## Critères d'échec

Une suite n'est pas verte si un test est ignoré sans justification, si une
redirection échappe à la validation SSRF, si une migration n'est testée que sur un
moteur de base, si un résultat dépend d'Internet, ou si un journal contient une
donnée sensible. Une fonctionnalité reportée doit rester explicitement marquée
comme telle dans `docs/development/progress.md`.
