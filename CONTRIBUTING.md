# Contribuer

Consulter `AGENTS.md` et `docs/development/contributing.md`. Toute contribution
doit inclure des tests, ne doit effectuer aucun scan Internet durant la CI et
doit respecter la portée OSINT autorisée.

Les pipelines ne publient aucun artefact externe. Ils conservent uniquement le
build frontend, et le rapport Playwright uniquement en cas d’échec, pendant sept
jours pour faciliter la revue. Consultez
`docs/development/contributing.md` pour reproduire leurs commandes localement.
