# Évaluation d'un connecteur Common Crawl

Évaluation réalisée le 24 octobre 2026 à partir de la documentation officielle
Common Crawl. La conclusion est de **ne pas intégrer de connecteur dans le
périmètre actuel**.

## Adéquation fonctionnelle

Common Crawl publie des index mensuels de captures et un corpus contenant des
données WARC, WAT et WET. L'index CDXJ est optimisé pour retrouver les captures
d'une URL connue ; il ne constitue pas un moteur de recherche de personnes. Les
contenus archivés doivent ensuite être lus par plage d'octets dans des fichiers
WARC. Le corpus complet représente plusieurs pétaoctets.

DigitalFootprint dispose déjà du connecteur Wayback, limité aux domaines et sites
renseignés par l'utilisateur. Ajouter Common Crawl maintenant dupliquerait cette
capacité sans améliorer la recherche par pseudonyme ou nom, tout en augmentant la
surface de traitement de contenus archivés.

## Contraintes opérationnelles et de sécurité

Le service CDX public est fortement limité en raison d'abus fréquents. Common
Crawl recommande HTTPS, des appels séquentiels espacés et un User-Agent descriptif.
Une réponse `503` impose de ralentir ; une adresse IP temporairement bloquée peut
devoir attendre 24 heures. Les traitements larges doivent utiliser l'URL Index
sur Athena ou Spark plutôt que le service public.

Le téléchargement des WARC ajouterait une seconde chaîne de décompression et
d'analyse de réponses HTTP archivées. Elle devrait appliquer des limites avant et
pendant la décompression, refuser les enregistrements non HTML, minimiser le texte
et ne jamais considérer l'ancienne réponse archivée comme une preuve actuelle.

## Conditions d'une future expérimentation

Un connecteur pourra être réévalué uniquement s'il respecte simultanément les
conditions suivantes :

- désactivation par défaut et activation administrative explicite ;
- requêtes limitées aux domaines, sites ou profils confirmés fournis par
  l'utilisateur, jamais aux noms, e-mails ou téléphones ;
- index sélectionné depuis la liste officielle, sans identifiant mensuel codé en
  dur, avec cache local et repli contrôlé ;
- budget maximal de cinq URL exactes et une requête séquentielle à la fois, quota
  persistant, temporisation et traitement explicite des `429`/`503` ;
- validation SSRF à chaque requête et redirection, validation stricte du schéma
  CDXJ, déduplication et plafonds de réponse ;
- première version limitée aux métadonnées de capture, sans téléchargement WARC ;
- provenance `common_crawl`, date de capture visible et avertissement qu'une
  archive ne démontre ni présence actuelle ni attribution à une personne ;
- tests entièrement hermétiques par transport HTTP simulé.

## Sources officielles

- [Common Crawl — CDXJ Index](https://commoncrawl.org/cdxj-index)
- [Common Crawl — FAQ](https://commoncrawl.org/faq)
- [Common Crawl — Get Started](https://commoncrawl.org/get-started)
- [Common Crawl — URL Index](https://commoncrawl.org/url-index)

