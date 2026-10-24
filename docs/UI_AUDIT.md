# Audit de l'interface

Audit statique et automatisé réalisé le 24 octobre 2026 sur les vues React.
Cette vérification ne remplace pas encore une recette visuelle multi-navigateurs.

## Périmètre examiné

- authentification et structure de navigation ;
- tableau de bord, identités, recherches et résultats ;
- surveillance, rapports et demandes de suppression ;
- données sensibles et administration ;
- catalogues de traductions français et anglais ;
- styles communs, tableaux, grilles, formulaires et états vides.

## Constat

Les tableaux de données sont contenus dans une zone horizontalement déroulante,
directement ou via leur panneau. Les grilles de métriques et de formulaires
restent sur une colonne par défaut puis s'élargissent aux points de rupture
`sm`, `md`, `lg` ou `xl`. Le contenu principal utilise `min-w-0`, ce qui évite
qu'un enfant large agrandisse toute la page.

Les actions à icône possèdent un libellé accessible. Le panneau de revue des
preuves ajoute un état `aria-expanded`, référence sa région avec
`aria-controls` et inclut le titre de la mention dans son nom accessible afin
de distinguer plusieurs boutons identiques. Les chargements et erreurs sont
affichés dans l'interface, et les écritures restent protégées par CSRF.

Les libellés fonctionnels sont centralisés en français et en anglais. Les noms
techniques provenant du backend (connecteur, méthode ou indicateur de prudence)
restent affichés comme données et ne sont pas présentés comme texte d'interface.

## Corrections et garanties couvertes

- résultats et contrôles de plateformes défilables sur petit écran ;
- filtres regroupés en grille responsive ;
- preuves chargées à la demande, sans requête par ligne au chargement ;
- scores de pertinence et d'attribution libellés séparément ;
- aucune case d'ajout aux profils confirmés précochée ;
- boutons de preuve nommés par résultat et région associée identifiable ;
- tests de composants sans réseau réel, build TypeScript, ESLint et Prettier.

## Reste à valider

Une recette visuelle avec captures aux largeurs mobile, tablette et bureau reste
nécessaire avant de déclarer la phase G terminée. Elle devra couvrir au minimum
les deux thèmes, les deux langues, les contenus longs, le clavier seul et les
principaux navigateurs pris en charge.
