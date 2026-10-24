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

## Revue des preuves

Chaque mention qui possède une corrélation propose « Examiner les preuves ».
Le panneau chargé à la demande distingue la pertinence du résultat de la
confiance d'attribution, rappelle que le score est heuristique et présente les
extraits bornés, les raisons de correspondance, le nombre de preuves
indépendantes et les indicateurs de prudence.

L'utilisateur peut confirmer, rejeter, marquer comme incertain ou exclure un
homonyme. Il peut corriger l'attribution vers un autre de ses profils et choisir
explicitement d'ajouter l'URL confirmée à ce profil. Ces écritures utilisent le
jeton CSRF ; aucune case d'ajout n'est cochée par défaut.

## Validation

Les textes français et anglais sont centralisés dans le catalogue i18n. Les tests
de composant utilisent des réponses synthétiques et vérifient le chargement à la
demande, la présentation prudente d'un résultat négatif et l'exclusion d'un
homonyme sans accès réseau réel. La validation comprend Vitest, TypeScript/Vite,
ESLint et Prettier.
