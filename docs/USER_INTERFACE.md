# Interface utilisateur

L'interface React réutilise les composants et styles existants. Elle propose les
sections tableau de bord, identités, recherches, résultats, surveillance,
administration et données sensibles selon les droits de la session.

## Contrôles de plateformes

Dans l'historique des recherches, une campagne terminée propose l'action
« Contrôles ». Elle charge à la demande
`GET /api/v1/scans/{scan_id}/platform-checks` et affiche :

- la plateforme évaluée ;
- la méthode déclarée ;
- le statut normalisé traduit ;
- le nombre de résultats publics observés ;
- la note méthodologique renvoyée par le backend.

Le chargement à la demande évite une requête par campagne lors de l'affichage de
l'historique. Le tableau est placé dans un conteneur horizontalement déroulant
sur les petits écrans et sa mise à jour est annoncée par `aria-live="polite"`.
`NO_PUBLIC_RESULT` est libellé « Aucun résultat public observé » et reste accompagné
de l'avertissement indiquant qu'il ne prouve pas l'absence d'un compte.

L'administration complète le catalogue avec la date du dernier contrôle et le
dernier code d'erreur contrôlé. Elle ne présente pas le statut par défaut comme
un résultat de campagne.

## Validation

Les textes français et anglais sont centralisés dans le catalogue i18n. Les tests
de composant utilisent des réponses synthétiques et vérifient le chargement à la
demande ainsi que la présentation prudente d'un résultat négatif. La validation
comprend Vitest, TypeScript/Vite, ESLint et Prettier.

