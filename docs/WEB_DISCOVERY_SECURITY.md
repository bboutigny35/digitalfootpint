# Sécurité de la découverte Web

La découverte traite toute URL et tout contenu distant comme non fiable. Le
modèle de menace général est détaillé dans
[`security/security-model.md`](security/security-model.md) ; ce document précise
les contrôles propres au crawler.

## Frontières de confiance

Les profils, validations et sources administratives appartiennent à la base de
confiance locale après authentification et autorisation. Les moteurs, index,
redirections, réponses DNS, robots.txt, sitemaps, flux et pages restent non
fiables, même lorsqu'une URL initiale a déjà été acceptée.

## SSRF et réseau

- résolution DNS avant connexion et refus des adresses loopback, privées,
  link-local, multicast, réservées ou non routables ;
- connexion liée à l'adresse validée tout en conservant la vérification du nom
  TLS, afin de réduire le risque de DNS rebinding ;
- nouvelle validation à chaque redirection, sans héritage de confiance ;
- refus par défaut lorsqu'un connecteur n'autorise pas explicitement le crawl ;
- endpoint SearXNG limité aux deux emplacements locaux connus ;
- timeouts, tailles, MIME, profondeur, nombre de documents et quotas bornés.

Ajouter une exception générique pour une plage privée est interdit. Une nouvelle
destination interne doit disposer d'un chemin dédié et testé sans affaiblir le
validateur des URL publiques.

## Minimisation et attribution

Le crawler ne conserve pas le corps HTML brut. Il persiste uniquement le texte
borné utile à l'analyse, une provenance, des empreintes, des liens admissibles et
les statistiques nécessaires. Les critères sensibles sont hachés par
propriétaire. Les scores de pertinence et d'attribution restent séparés ; un nom
seul est plafonné et signalé comme ambigu.

Les validations confirmer, rejeter, incertain ou homonyme sont privées. Leur
réutilisation est limitée au même propriétaire. Aucun résultat ne doit être
présenté comme une preuve certaine d'identité.

## Consentement, secrets et journaux

Les moteurs généralistes exigent un consentement explicite. Les e-mails exacts ne
leur sont pas transmis. Les secrets fournisseurs sont chiffrés dans le coffre et
ne doivent apparaître ni dans les arguments, ni dans les réponses, ni dans les
journaux. Les journaux utilisent des codes d'erreur génériques et excluent URL,
contenu, e-mail complet et donnée d'identité.

## Revue d'une nouvelle source

Avant activation : confirmer l'interface autorisée, les conditions d'utilisation,
robots.txt, quotas, données transmises, durée de conservation, provenance et
méthode de révocation. Ajouter des tests avec transport HTTP simulé pour DNS,
redirections, limites, réponses malformées et journaux. Une revue juridique reste
obligatoire avant tout fournisseur externe réel.
