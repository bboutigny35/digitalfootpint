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

## Sources Web

Un administrateur peut enregistrer une URL de base via l'interface ou
`POST /api/v1/admin/web-sources`. L'entrée est créée dans l'état `pending` et ne
déclenche aucun accès réseau. Avant toute découverte ou exploration future, son
URL devra passer par le validateur SSRF et chaque redirection sera revalidée.
L'API ne permet pas encore de la marquer `active` : cette transition sera ajoutée
avec le contrôle réseau sécurisé du lot d'exploration.

Le registre conserve catégorie, méthode d'accès, priorité, politique de cache,
limite de fréquence, restrictions, compteurs minimisés, dernier contrôle et
dernier code d'erreur. Les erreurs ne doivent contenir ni URL sensible complète,
ni identité, ni secret.
