# Procédure de release

DigitalFootprint suit [Semantic Versioning 2.0.0](https://semver.org/) et utilise
les Conventional Commits. Cette procédure prépare une release de façon
reproductible ; elle n'autorise ni publication distante ni déploiement en
production.

## État et trajectoire

La version publique courante est `0.1.0-dev.0`. Le paquet Python utilise son
équivalent PEP 440 `0.1.0.dev0`. Aucun tag historique ni remote n'est configuré au
25 octobre 2026.

Le projet reste en série `0.x` tant que les contrats publics, la revue juridique
des fournisseurs externes et les critères de la première version ne sont pas
figés. Une fois ces critères satisfaits, la progression prévue est
`1.0.0-beta.1`, puis `1.0.0-rc.1`, puis `1.0.0`. Une correction rétrocompatible
incrémente PATCH, une fonctionnalité rétrocompatible MINOR et une incompatibilité
MAJOR. Avant `1.0.0`, toute incompatibilité doit néanmoins être annoncée dans le
changelog.

## Préparer une version

1. Vérifier que `git status --short` est vide et examiner les commits depuis le
   dernier tag. En l'absence de tag, examiner tout l'historique.
2. Exécuter les contrôles de `docs/development/contributing.md`, notamment les
   suites backend/frontend, migrations SQLite/PostgreSQL, E2E, audits de
   dépendances, builds Compose et génération documentaire.
3. Rechercher les migrations destructives et les commits comportant `!` ou un
   pied de message `BREAKING CHANGE:`. Une incompatibilité non documentée bloque
   la release.
4. Déplacer les éléments pertinents de `Non publié` dans `CHANGELOG.md` sous une
   section `X.Y.Z — AAAA-MM-JJ`, puis recréer une section `Non publié` vide.
5. Calculer la version selon SemVer. Ne jamais réutiliser ni déplacer un tag
   publié.
6. Mettre à jour ensemble les métadonnées suivantes :

   - `backend/app/version.py` avec la version SemVer publique ;
   - `backend/pyproject.toml` avec l'équivalent PEP 440 ;
   - `frontend/package.json` et `frontend/package-lock.json` avec SemVer.

   Les correspondances de prépublication sont :

   | SemVer public | Python / PEP 440 |
   | --- | --- |
   | `1.0.0-beta.1` | `1.0.0b1` |
   | `1.0.0-rc.1` | `1.0.0rc1` |
   | `1.0.0` | `1.0.0` |

7. Rejouer au minimum les tests de version, le build frontend et les validations
   complètes affectées. Contrôler aussi la version OpenAPI et l'aperçu admin.
8. Créer un unique commit local `chore(release): prepare X.Y.Z` et vérifier son
   contenu.

## Taguer et vérifier

Le tag annoté et toute publication exigent une autorisation explicite. Après
validation humaine du commit de release :

```bash
git tag -a vX.Y.Z -m "DigitalFootprint X.Y.Z"
git show --verify --stat vX.Y.Z
```

Vérifier que le tag cible le commit de release, que le dépôt reste propre et que
les trois métadonnées représentent la même version. Un push, une release sur une
forge, une publication d'image ou un déploiement de production font l'objet
d'une autorisation distincte.

## Annulation

Avant publication, corriger le commit de préparation par un nouveau commit. Si un
tag local erroné n'a jamais été partagé, demander une validation explicite avant
de le supprimer et en recréer un. Après publication, ne jamais déplacer le tag :
publier une version corrective selon SemVer.
