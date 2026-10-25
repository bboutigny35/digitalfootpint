# Revue contractuelle préliminaire des fournisseurs

État au 25 octobre 2026. Ce document est un inventaire technique des textes
officiels, pas un avis juridique. L'activation réelle reste soumise à la décision
d'une personne compétente, au contexte d'utilisation et, le cas échéant, au plan
commercial effectivement souscrit.

## Conclusion opérationnelle

Brave Search reste bloqué par défaut, même lorsqu'une clé est enregistrée. Son
activation exige désormais `DIGITALFOOTPRINT_BRAVE_CONTRACT_APPROVED=true`, qui
ne doit être défini qu'après confirmation écrite de droits compatibles avec la
persistance des résultats et l'usage exact de DigitalFootprint. Le consentement
de l'utilisateur au moment du scan reste exigé séparément.

Les autres connecteurs conservent leurs limites locales, la minimisation et les
tests hermétiques. Leur présence dans le code ne constitue pas une approbation
juridique générale ni une autorisation de traiter les données d'un tiers.

## Brave Search API — blocage

Références officielles consultées :

- [Search API Terms of Use, 1er septembre 2026](https://api-dashboard.search.brave.com/documentation/resources/terms-of-service) ;
- [Privacy Notice, 25 août 2026](https://api-dashboard.search.brave.com/documentation/resources/privacy-notice) ;
- [présentation et tarifs de l'API](https://brave.com/search/api/).

Points nécessitant une validation explicite :

- les conditions interdisent par défaut de stocker, mettre en cache ou constituer
  une base de résultats au-delà du stockage transitoire nécessaire ; la page
  commerciale indique que certains plans peuvent inclure des droits de stockage ;
- les usages interdits mentionnent notamment la surveillance, notion dont
  l'application au suivi volontaire de sa propre empreinte doit être clarifiée ;
- le client doit fournir ses propres notices, recueillir les consentements requis
  et encadrer contractuellement les utilisateurs finaux ;
- les requêtes peuvent être conservées jusqu'à 90 jours pour facturation et
  diagnostic ;
- les frais, crédits, restrictions après résiliation, indemnisation et droit
  californien doivent être acceptés par l'entité qui exploite l'instance.

La simple possession d'une clé API ne répond pas à ces questions. Le verrou
opérateur empêche aussi le worker d'injecter une clé issue du coffre lorsque
l'approbation contractuelle est absente.

## GitHub

Références officielles : [conditions, section API](https://docs.github.com/en/site-policy/github-terms/github-terms-of-service#h-api-terms)
et [limites REST](https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api).

Les conditions interdisent notamment le téléchargement via API à des fins de
spam ou de vente d'informations personnelles et le contournement des quotas.
DigitalFootprint limite la consultation aux profils publics correspondant à des
pseudonymes fournis, ne revend pas les données et applique un quota local. Une
revue reste nécessaire pour un déploiement multi-utilisateur ou commercial.

## GitLab

La [page officielle des conditions](https://about.gitlab.com/terms/) rattache les
API publiques aux API Terms of Use, à l'Acceptable Use Policy et à la Privacy
Statement. Le connecteur actuel n'envoie qu'un pseudonyme, interroge un endpoint
public précis, ne conserve pas le statut distant et applique un quota local.
L'exploitant doit néanmoins vérifier la version contractuelle applicable à son
compte et à son territoire.

## Bluesky / AT Protocol

Références officielles : [conditions Bluesky](https://bsky.social/about/support/tos)
et [documentation AT Protocol](https://docs.bsky.app/).

Le connecteur résout exactement un handle par l'interface publique, sans nom ni
e-mail et sans contourner l'authentification. Les conditions rappellent toutefois
que les applications tierces restent responsables de leurs propres pratiques,
des droits sur les contenus et des lois applicables. La nature fédérée implique
aussi qu'une suppression ne se propage pas nécessairement à tous les services.

## Internet Archive / Wayback

Le connecteur utilise uniquement CDX pour les domaines fournis par l'utilisateur,
avec résultats et volumes bornés. Les conditions officielles sont publiées sur
[archive.org/about/terms](https://archive.org/about/terms). Leur rendu nécessite
JavaScript lors de la revue automatisée ; une lecture humaine de la version
applicable et des règles propres aux API reste donc requise avant un usage autre
que personnel et contrôlé.

## SearXNG

SearXNG est auto-hébergé, mais relaie les requêtes aux moteurs configurés. Chaque
moteur amont conserve ses propres conditions, quotas et politiques. L'exploitant
doit limiter la liste aux moteurs qu'il est autorisé à utiliser ; DigitalFootprint
n'autorise ni contournement de CAPTCHA ni mesure anti-bot.

## Validation attendue

Pour lever un blocage fournisseur, consigner au minimum : entité contractante,
plan et date, territoire, finalité, catégories de données, base légale, durée de
conservation, droits de stockage/affichage, sous-traitants, procédure de retrait,
coûts et personne ayant validé. Réexaminer les textes avant chaque release et
après toute notification de modification.
