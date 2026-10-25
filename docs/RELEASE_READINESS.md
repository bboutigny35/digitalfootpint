# État de préparation de release

Évaluation du 25 octobre 2026. Le projet reste en version `0.1.0-dev.0` et aucun
tag de release n'est créé par cette revue.

## Contrôles validés

- arbre Git propre au début de la revue et historique Conventional Commits sans
  marqueur `BREAKING CHANGE` ni commit `!` détecté ;
- 200 tests backend collectés : suite complète réussie avec une intégration
  PostgreSQL opt-in ignorée par défaut, Ruff et mypy strict réussis ;
- 26 tests frontend, ESLint, TypeScript, Prettier et build Vite réussis ;
- parcours Playwright Chromium complet, quatre audits axe représentatifs et
  absence de débordement global aux largeurs mobile et tablette ;
- audits `pip-audit --strict` et `npm audit --audit-level=moderate` sans
  vulnérabilité connue lors de la revue finale ;
- migrations SQLite et PostgreSQL, images Compose, installation Debian 13,
  sauvegarde/restauration réelle et arrêt/reprise du worker déjà exercés ;
- dernier déploiement sur `DEB13-TEST` sauvegardé, transféré avec empreinte
  SHA-256 concordante et validé par les unités et sondes locales ;
- Brave bloqué par défaut tant qu'une approbation contractuelle opérateur et une
  clé ne sont pas toutes deux configurées.

## Conditions encore bloquantes

1. Obtenir et consigner une validation juridique et contractuelle externe avant
   toute activation réelle de Brave ou d'un autre fournisseur non approuvé.
2. Réaliser la recette manuelle exhaustive annoncée : navigation clavier de tous
   les formulaires, contenus extrêmes et navigateurs supplémentaires.
3. Obtenir les pipelines GitHub verts sur de vrais runners après le premier push.
   GitLab reste non configuré et n'est donc pas vérifié à distance.
4. Choisir explicitement la version à publier après ces validations, préparer le
   changelog et les trois métadonnées de version dans un même commit, puis faire
   valider ce commit avant le tag annoté.

## Décision

Le code est prêt pour poursuivre une recette de prépublication contrôlée, mais
pas pour déclarer une version stable ni activer Brave. Le dépôt GitHub privé est
publié, mais le résultat de ses workflows n'est pas encore confirmé. Ces limites
ne sont pas remplacées par les tests locaux et ne doivent pas être requalifiées
en contrôles réussis.
