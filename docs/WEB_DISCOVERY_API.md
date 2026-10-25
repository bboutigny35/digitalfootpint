# API de découverte Web

Toutes les routes sont sous `/api/v1`, utilisent la session locale et appliquent
l'isolation par propriétaire. Les opérations d'écriture exigent le jeton CSRF.
Les schémas exacts et codes de réponse sont disponibles dans OpenAPI sur `/docs`.

## Profils et plan de recherche

- `GET /profiles/{profile_id}/search-strategy` : prévisualise le plan borné sans
  créer de campagne ni effectuer d'accès réseau.
- `POST /profiles`, `PUT /profiles/{profile_id}` : créent ou modifient les
  identifiants structurés utilisés par la stratégie.

## Campagnes et file de crawl

- `POST /scans` : crée une campagne et ses tâches ; les moteurs généralistes
  exigent le consentement prévu par leur contrat.
- `GET /scans/{scan_id}` : état de la campagne appartenant à l'utilisateur.
- `GET /scans/{scan_id}/crawl` : compteurs agrégés de la file, sans URL brute.
- `POST /scans/{scan_id}/crawl/pause` et `/crawl/resume` : suspendent ou reprennent
  la consommation ; aucune requête distante n'est exécutée dans l'appel API.
- `GET /scans/{scan_id}/platform-checks` : contrôles normalisés des plateformes
  réellement évaluées, avec limites méthodologiques.

Les scans sont asynchrones. Un `201` signifie mise en file, pas disponibilité ni
exactitude d'un résultat externe.

## Résultats et corrélation

- `GET /results` et `GET /results/search` : résultats isolés et paginés.
- `GET /results/{result_id}/correlation` : preuves minimisées, provenance,
  correspondances et scores distincts de pertinence/attribution.
- `PUT /results/{result_id}/validation` : décision privée et correction
  d'attribution vers un profil appartenant au même compte.
- `PATCH /results/{result_id}` : validation historique du résultat et ajout
  explicitement demandé d'une URL confirmée au profil.

Les réponses négatives d'une plateforme ne prouvent jamais l'absence de compte.

## Administration des sources

- `GET /admin/platform-catalog` : catalogue et méthode disponible.
- `GET /admin/web-sources` : registre des sources.
- `POST /admin/web-sources` : ajoute une source en état `pending`.
- `PATCH /admin/web-sources/{source_id}` : modifie priorité, restrictions ou état
  après revue administrative.

Ces routes sont réservées à l'administrateur. Elles configurent la découverte
mais ne téléchargent pas la source pendant la requête HTTP.

## Erreurs et confidentialité

Les réponses utilisent `401` pour une session absente, `403` pour CSRF/rôle ou
propriété, `404` pour une ressource invisible, `409` pour un conflit et `422` pour
une entrée invalide. Les erreurs de fournisseur sont normalisées et ne révèlent
ni secret ni détail d'identité.
