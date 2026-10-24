# Catalogue des plateformes et connecteurs

Le catalogue administratif distingue une plateforme d'un connecteur exécutable.
Une plateforme peut donc être documentée même lorsqu'aucune vérification publique
fiable ou autorisée n'existe.

## Statuts normalisés

- `PUBLIC_MATCH` : correspondance publique étayée ;
- `POSSIBLE_MATCH` : indices insuffisants pour confirmer ;
- `NO_PUBLIC_RESULT` : aucun résultat public observé pendant le contrôle ;
- `USER_VERIFIED` : contrôle confirmé directement par le titulaire ;
- `NOT_VERIFIABLE` : aucune méthode publique fiable et autorisée ;
- `RATE_LIMITED`, `ACCESS_RESTRICTED` et `ERROR` : contrôle non conclusif.

`NO_PUBLIC_RESULT` et `NOT_VERIFIABLE` ne prouvent jamais l'absence d'un compte.

## Méthodes

Le catalogue décrit `official_api`, `public_profile`, `public_index`,
`user_verification` ou `none`. Netflix, Disney+, Epic Games et les autres
services sans annuaire public ne sont jamais interrogés comme des annuaires de
clients. Aucune connexion, récupération de mot de passe, énumération de comptes
ou tentative de contournement n'est permise.

Les connecteurs réellement exécutables restent enregistrés dans le registre
typé existant et activés par `ConnectorConfiguration`. Le catalogue ne duplique
pas cet état : `connector_id` est nul tant qu'aucune implémentation compatible
n'existe.

## Contrôles par campagne

La migration `0017` ajoute un résultat normalisé par campagne et plateforme.
Lorsqu'un connecteur sélectionné a réellement été exécuté, au moins un résultat
produit `PUBLIC_MATCH` et l'absence de résultat produit `NO_PUBLIC_RESULT`. Ce
dernier statut décrit uniquement le contrôle réalisé ; il ne prouve pas qu'aucun
compte n'existe.

Les méthodes `none` et `user_verification` produisent `NOT_VERIFIABLE` sans accès
réseau. Une plateforme disposant théoriquement d'un profil public mais sans
connecteur exécuté ne reçoit aucun résultat artificiel. La finalisation est dans
la même transaction que la fin de la campagne et reste idempotente.

Le propriétaire consulte ces états avec
`GET /api/v1/scans/{scan_id}/platform-checks`. L'API ne renvoie aucune donnée
d'une campagne appartenant à un autre utilisateur et inclut une note de méthode.

## Connecteur Bluesky

Bluesky utilise l'endpoint public officiel AT Protocol
`com.atproto.identity.resolveHandle`. Seuls les pseudonymes ayant la forme d'un
handle DNS exact sont envoyés ; les noms, e-mails et pseudonymes libres sont
exclus. Une campagne effectue au plus dix résolutions, séquentiellement, sous un
quota persistant de dix requêtes par minute. Les redirections sont refusées et
une réponse n'est acceptée que si elle contient un DID syntaxiquement valide.

L'évaluation du 24 octobre 2026 a reporté Gravatar, car l'API de profil moderne
requiert une clé, ainsi que Docker Hub et npm, dont la documentation ne fournit
pas de contrôle public exact suffisamment stable sans authentification ou route
héritée. Aucun endpoint non documenté n'est utilisé.

Sources officielles :

- [Bluesky — référence HTTP API](https://docs.bsky.app/docs/api/com-atproto-identity-resolve-handle)
- [Gravatar — profils par identifiant](https://docs.gravatar.com/rest/api-data-specifications/endpoints-references/)
- [Docker Hub API](https://docs.docker.com/reference/api/hub/latest/)
- [npm — registre public](https://docs.npmjs.com/using-npm/registry.html/)

## Sources Web

Un administrateur peut enregistrer une URL de base via l'interface ou
`POST /api/v1/admin/web-sources`. L'entrée est créée dans l'état `pending` et ne
déclenche aucun accès réseau. Avant toute découverte ou exploration future, son
URL devra passer par le validateur SSRF et chaque redirection sera revalidée.
L'administrateur peut ensuite la marquer explicitement `active`; cette transition
ne déclenche elle-même aucun téléchargement.

Le registre conserve catégorie, méthode d'accès, priorité, politique de cache,
limite de fréquence, restrictions, compteurs minimisés, dernier contrôle et
dernier code d'erreur. Les erreurs ne doivent contenir ni URL sensible complète,
ni identité, ni secret.
