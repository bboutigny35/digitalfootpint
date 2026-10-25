# Configuration de la découverte Web

La découverte Web est désactivée tant qu'aucune source ou aucun connecteur
compatible n'est activé. Elle réutilise le profil d'identité, la file persistante
et le worker ; elle ne possède pas de service réseau autonome.

## Stratégies

L'aperçu privé `GET /api/v1/profiles/{id}/search-strategy` produit un plan
déterministe en mode rapide, standard ou approfondi. Les budgets, priorités et
critères proviennent du code et restent bornés. Un e-mail exact n'est jamais
envoyé à un moteur généraliste et une requête sur le nom seul exige une
corroboration.

Le mode choisi est fourni à la création du scan. Les connecteurs réellement
utilisables dépendent de leur activation, de leurs identifiants compatibles et de
leurs éventuels secrets. L'interface « Recherche globale » ne sélectionne que les
connecteurs activés et prêts.

## Variables d'environnement

Les paramètres communs sont décrits dans
[`administration/configuration.md`](administration/configuration.md) et
`.env.example`. Ceux qui affectent directement la découverte sont :

| Variable                                       | Rôle                                                                                                   |
| ---------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| `DIGITALFOOTPRINT_SCAN_WORKER_POLL_SECONDS`    | Intervalle de scrutation du worker, de 0,2 à 60 s.                                                     |
| `DIGITALFOOTPRINT_GITHUB_API_TOKEN`            | Jeton GitHub facultatif ; préférer le coffre administrateur.                                           |
| `DIGITALFOOTPRINT_BRAVE_API_TOKEN`             | Compatibilité facultative ; préférer le coffre administrateur.                                         |
| `DIGITALFOOTPRINT_SEARXNG_URL`                 | Vide/désactivée, `http://127.0.0.1:8888/search` en natif ou `http://searxng:8080/search` avec Compose. |
| `DIGITALFOOTPRINT_CONNECTOR_SECRET_KEYS`       | Liste des clés de chiffrement du coffre, de l'ancienne à l'active.                                     |
| `DIGITALFOOTPRINT_CONNECTOR_SECRET_ACTIVE_KEY` | Version active utilisée pour les nouveaux secrets.                                                     |

Une URL SearXNG arbitraire est refusée. Après modification d'un secret dans le
coffre, le worker recharge le registre avant chaque scan sans redémarrage manuel.

## Sources administratives

Une source ajoutée par `POST /api/v1/admin/web-sources` reste `pending`. Un
administrateur doit vérifier sa méthode d'accès, son domaine, ses restrictions,
son quota et sa durée de cache avant de la passer à `active`. Les méthodes prises
en charge par la découverte sont les sitemaps et les flux RSS/Atom. Une campagne
planifie au plus 20 sources actives, dans un ordre déterministe.

Les résultats d'un connecteur n'alimentent le crawler que si le connecteur le
déclare explicitement. Toute URL est à nouveau validée avant sa mise en file.

## Limites opérationnelles

- trois tentatives au maximum par tâche avec recul borné ;
- bail de cinq minutes et reprise des baux expirés ;
- robots.txt, quota par domaine, taille et types MIME bornés ;
- cache persistant afin d'éviter un nouveau téléchargement prématuré ;
- contenu brut non conservé, texte et métadonnées minimisés ;
- aucune promesse d'exhaustivité, d'identité ou de disponibilité des sources.

Les détails de déploiement figurent dans
[`WEB_DISCOVERY_DEPLOYMENT.md`](WEB_DISCOVERY_DEPLOYMENT.md).
