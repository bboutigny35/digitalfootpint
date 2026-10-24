# Exposition des données sensibles

Ouvrez **Sécurité > Données sensibles** après connexion. L'écran permet de valider
un NIR ou un numéro de pièce de façon éphémère, de surveiller un téléphone, un
IBAN ou une adresse sous forme masquée, et de référencer une carte uniquement par
son réseau et ses quatre derniers chiffres.

Les libellés fixes de cet écran suivent la langue de l’interface. Les noms de
fournisseurs, recommandations reçues et messages d’erreur externes restent dans
la langue fournie par leur source. Les avertissements de sécurité restent
visibles dans les deux langues et les identifiants complets ne sont jamais
affichés.

Ne saisissez jamais de PAN complet, CVV/CVC, code PIN ou mot de passe bancaire.
DigitalFootprint ne recherche pas ces données sur Internet et n'interroge aucune
base volée.

## Alertes

Une alerte issue d'une source autorisée indique la catégorie, la source, la date,
le niveau de risque et une mesure recommandée. Elle ne contient jamais la valeur
sensible complète. Le bouton **Marquer comme traitée** enregistre uniquement la
date de prise en compte et un événement d'audit non sensible.

Une absence d'alerte n'est pas une preuve d'absence de compromission. Une alerte
doit être vérifiée auprès de l'organisme ou du fournisseur officiel concerné.

## Suppression et conservation

La suppression d'un élément surveillé retire son masque et son empreinte protégée.
Les historiques associés suivent les règles décrites dans la
[politique de conservation](../security/data-retention.md). En installation native,
un timer quotidien supprime les descripteurs expirés par lots tout en conservant
l'historique non sensible avec une référence devenue nulle.
