# Corrélation d'identité

La pertinence d'un résultat et la confiance dans son attribution sont deux
mesures distinctes. Elles sont heuristiques, explicables et ne sont jamais
présentées comme des probabilités statistiques validées.

## Preuves et provenance

`Evidence` conserve un extrait borné, l'URL source, une empreinte de source, la
date d'observation et une provenance structurée. `EvidenceMatch` associe une
preuve à un type de critère et à une empreinte de valeur : une adresse e-mail ou
un téléphone brut n'est pas recopié dans la table de correspondance.

Les copies d'une même source peuvent être reconnues par `source_hash` et ne
doivent pas être comptées comme preuves indépendantes.

L'analyseur `exact-identity-evidence-v1` traite actuellement la page racine
d'un résultat de connecteur après son crawl. Il recherche uniquement des valeurs
exactes normalisées (nom complet, variantes, pseudonymes, e-mail public,
localisation, profession et employeurs), ainsi que le domaine ou l'URL déjà
connus. Les critères sont enregistrés sous forme d'empreintes isolées par
propriétaire. Une page secondaire découverte par un lien n'est jamais attribuée
implicitement au résultat parent.

## Attribution

Les signaux discriminants (profil confirmé, e-mail public, domaine connu,
pseudonyme et liens entre profils) pèsent davantage que le nom. Un nom seul est
plafonné à un indice faible et exige toujours une corroboration. Chaque
contradiction distincte réduit l'indice, par exemple une localisation ou un
employeur incompatibles.

`IdentityCorrelation` conserve séparément `relevance_score`,
`attribution_score`, les facteurs explicatifs, contradictions et nombre de
preuves. La méthode courante est versionnée
`identity-attribution-signals-v1`.

Cette première version ne fait pas de rapprochement approximatif. Une
correspondance sur le nom seul reste donc faible et aucune absence de signal
n'est transformée automatiquement en faux positif. Les exclusions explicites du
profil sont conservées comme contradiction générique, sans recopier leur valeur
dans l'explication.

## Validation humaine

`UserValidation` enregistre une décision par propriétaire et corrélation. Les
décisions prévues sont confirmation, rejet et incertitude ; un rejet peut
identifier un homonyme ou une autre exclusion. La contrainte inclut toujours
`owner_id` afin qu'une validation ne soit jamais réutilisée entre utilisateurs.
