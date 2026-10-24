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

L'analyseur `identity-evidence-v2` traite actuellement la page racine
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

Le rapprochement approximatif est limité au nom, sur un texte et un nombre de
termes bornés, avec un seuil explicite. Il est ignoré tant qu'un signal plus
discriminant (pseudonyme, e-mail public, employeur, domaine ou URL connue) ne le
corrobore pas. Une correspondance sur le nom seul reste faible, porte les
indicateurs `name_only` et `possible_homonym`, et aucune absence de signal n'est
transformée automatiquement en faux positif.

Une classification lexicale bornée signale les contextes d'organisation, de
lieu ou rue, d'œuvre et de profil personnel. Il s'agit d'indicateurs de risque
explicables, pas d'une reconnaissance d'entités statistique ni d'une décision
automatique. Les exclusions explicites du profil sont conservées comme
contradiction générique, sans recopier leur valeur dans l'explication.

Avant de compter une preuve comme indépendante, l'analyseur recherche une
preuve antérieure du même propriétaire avec la même empreinte de contenu. La
copie reste consultable et sa provenance référence la première preuve, mais son
`evidence_count` vaut zéro afin de ne pas gonfler le nombre de sources.

## Validation humaine

`UserValidation` enregistre une décision par propriétaire et corrélation. Les
décisions prévues sont confirmation, rejet et incertitude ; un rejet peut
identifier un homonyme ou une autre exclusion. La contrainte inclut toujours
`owner_id` afin qu'une validation ne soit jamais réutilisée entre utilisateurs.

Le propriétaire consulte les preuves avec
`GET /api/v1/results/{result_id}/correlation` et enregistre sa décision avec
`PUT /api/v1/results/{result_id}/correlation/validation`, protégé par CSRF. Il
peut désigner un autre de ses profils comme attribution correcte et, uniquement
sur confirmation explicite, ajouter l'URL aux profils confirmés. Les empreintes
internes des critères ne sont pas renvoyées par l'API.

Lorsqu'une campagne ultérieure retrouve exactement la même URL canonique pour
le même propriétaire, la dernière validation est recopiée avec une référence à
sa source et son statut de vérification est appliqué. Cette réutilisation ne
modifie ni les preuves ni le score heuristique et la requête impose l'égalité de
`owner_id` ; aucune décision n'est partagée entre comptes.
