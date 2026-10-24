# Plan d'implémentation et critères d'acceptation

## Phase 0

Acceptée lorsque l'environnement, les contraintes, l'architecture, les versions,
le modèle, la menace, l'arborescence et le suivi sont documentés. La validation
Debian réelle est reportée explicitement à la phase 5.

## Phase 1

Acceptée quand migrations SQLite et PostgreSQL passent en aller/retour, que les
tests auth/CSRF/propriété CRUD sont verts, que Ruff et mypy passent, que l'OpenAPI
est générée, et qu'aucun secret/donnée sensible n'apparaît dans les logs.

## Phase 2

Acceptée quand un scan GitHub officiel et un connecteur simulé passent par la même
interface ; une tâche survit à un redémarrage ; annulation, bail, timeout, retries,
quota, concurrence, déduplication et score expliqué sont testés hors réseau ; les
tests SSRF couvrent DNS, redirections et toutes les plages interdites.

## Phase 3

Acceptée quand l'utilisateur peut se connecter, gérer une identité, lancer/suivre
un scan et filtrer/valider ses résultats depuis desktop et mobile ; typecheck,
lint, tests composants, accessibilité de base, build et parcours Playwright passent.

## Phase 4

Acceptée quand les périodicités créent des scans persistants sans doublon, deux
scans sont comparables sans confondre indisponible et supprimé, les cinq formats
d'export passent leurs tests d'injection/autorisation, et aucune demande RGPD ne
part sans confirmation explicite.

## Phase 5

Acceptée quand installation, mise à jour, sauvegarde/restauration et désinstallation
sont testées sur Debian 13 ; Compose démarre en non-root avec healthchecks et
persistance ; systemd redémarre Web/worker ; Nginx écoute localement par défaut et
la procédure HTTPS est reproductible.

## Phase 6

Acceptée quand CI GitHub/GitLab, audits, E2E, couverture convenue, génération PDF,
revue sécurité, changelog et procédure de version sont verts. La v0.1 exige en plus
les douze critères fonctionnels du cahier des charges, démontrés et documentés.
