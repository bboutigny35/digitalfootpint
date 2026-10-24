# Avancement

Dernière mise à jour : 24 octobre 2026.

## Phase A — audit de découverte Web (24 octobre 2026)

- [x] Auditer l'architecture, les modèles, connecteurs, API, interface, sécurité,
      tests, déploiements, documentation, version et état Git existants.
- [x] Documenter les acquis, les écarts à la chaîne de découverte/crawl/corrélation,
      les risques de régression et le plan additif dans
      `docs/WEB_DISCOVERY_AUDIT.md`.
- [x] Inventorier DEB13-TEST sans modification destructive dans
      `docs/TEST_ENVIRONMENT.md` : domaine persistant arrêté, 2 vCPU, 2 Gio,
      interface virtio sur le réseau libvirt `default`, aucun snapshot listé.
- [x] Contrôler DEB13-TEST après démarrage du réseau par l'utilisateur : UUID
      conforme, Debian 13.7, ressources disponibles, DNS et HTTPS sortant
      fonctionnels, services actifs et sondes application/SearXNG HTTP 200.
- [x] Revalider localement le socle : suite backend complète réussie avec un test
      PostgreSQL optionnel ignoré, Ruff et mypy strict réussis ; frontend 24 tests,
      build Vite, ESLint et Prettier réussis.
- [x] Autorisation reçue de créer l'historique initial après contrôle des fichiers
      et recherche de secrets ; aucun remote ni tag n'est configuré.

La phase A est **terminée** et figée par le commit initial `c110649`. Aucun tag de
release ni push distant n'est autorisé à ce stade.

## Phase B — architecture de découverte Web

- [x] Définir l'architecture additive et la séquence des migrations dans
      `docs/WEB_DISCOVERY_ARCHITECTURE.md`.
- [x] Ajouter un moteur déterministe de stratégie avec modes rapide, standard et
      approfondi, budgets stricts, priorités et déduplication.
- [x] Empêcher les plans d'envoyer un e-mail exact aux moteurs généralistes et
      marquer toute requête sur le nom seul comme nécessitant une corroboration.
- [x] Exposer une prévisualisation privée du plan par profil, sans accès réseau ni
      création de campagne.
- [x] Valider le moteur et l'API par tests ciblés, puis la suite backend complète,
      Ruff et mypy strict.
- [x] Ajouter la migration additive `0012` et les champs d'identité structurés,
      avec normalisation Unicode, espaces, casse et téléphone conservatrice.
- [x] Raccorder l'édition React aux nouveaux champs afin de préserver leur valeur,
      avec libellés FR/EN et contrôles TypeScript, Vitest, build, ESLint et Prettier.
- [x] Valider `0012` en montée, rétrogradation vers `0011` et remontée sur SQLite
      et PostgreSQL 17 UTF-8 éphémères ; suite backend complète, Ruff et mypy
      strict réussis.
- [x] Implémenter `0013` avec catalogue de 32 plateformes et registre des sources
      Web, sans dupliquer l'activation des connecteurs existants.
- [x] Ajouter les API et vues administratives de consultation du catalogue et
      d'ajout manuel de sources, créées en état `pending` sans accès réseau.
- [x] Valider `0013` en montée, rétrogradation vers `0012` et remontée sur SQLite
      et PostgreSQL 17 UTF-8, avec contrôle des 32 entrées initiales.
- [x] Implémenter `0014` : URL découvertes, tâches de crawl à baux, résultats
      minimisés, expiration du cache et statistiques persistantes par campagne.
- [x] Ajouter une mise en file déterministe avec canonicalisation, empreinte
      SHA-256, déduplication, profondeur/priorité bornées et premier filtrage des
      URL manifestement interdites, sans accès réseau.
- [x] Valider `0014` en montée, rétrogradation vers `0013` et remontée sur SQLite
      et PostgreSQL 17 UTF-8 ; six tests dédiés, suite backend complète, Ruff et
      mypy strict réussis.
- [x] Ajouter `0015` pour les preuves, correspondances minimisées, corrélations
      séparant pertinence et attribution, contradictions et validations privées.
- [x] Implémenter un score d'attribution explicable, plafonner le nom seul et
      pénaliser les contradictions sans présenter le résultat comme probabilité.
- [x] Valider `0015` en montée, rétrogradation vers `0014` et remontée sur SQLite
      et PostgreSQL 17 UTF-8 ; suite backend complète, Ruff et mypy réussis.

La phase B est **terminée pour l'architecture et les fondations persistantes**.
Les moteurs qui alimenteront ces modèles, leurs API et leurs interfaces relèvent
des phases C à G et ne sont pas encore déclarés opérationnels.

## Phase C — planificateur et crawler

- [x] Ajouter l'acquisition atomique par priorité avec bail de cinq minutes,
      reprise des baux expirés et limite de trois tentatives.
- [x] Respecter un `Retry-After` borné ou appliquer un recul exponentiel avec
      jitter, puis comptabiliser les échecs définitifs.
- [x] Exposer au propriétaire l'état agrégé de sa file et les contrôles pause /
      reprise protégés par CSRF, sans déclencher d'accès réseau.
- [x] Implémenter le fetcher HTTP avec robots.txt, quotas par domaine, limites de
      taille/MIME et validation SSRF à chaque résolution et redirection.
- [x] Extraire et persister atomiquement le contenu minimisé, les liens de même
      hôte admissibles, le cache et la provenance, sans conserver le corps brut.
- [x] Raccorder le worker aux tâches de crawl, aux erreurs permanentes ou
      récupérables, à la reprise bornée et à l'arrêt gracieux.

La phase C est **terminée pour son périmètre d'implémentation** : planification,
fetcher sécurisé, minimisation et worker sont couverts sans accès réseau par des
transports HTTP simulés. Le déploiement sur DEB13-TEST et une validation contrôlée
en environnement réel restent des opérations séparées, non exécutées ici.

## Phase D — découverte Web

- [x] Normaliser les candidats issus de sitemaps, index de sitemaps, RSS et Atom
      dans un contrat commun, avec analyse XML durcie par `defusedxml`.
- [x] Borner la taille et le nombre d'éléments, refuser DTD/entités, URL hors
      domaine et sources inactives, puis mettre les pages en file avec provenance.
- [x] Permettre à l'administrateur d'activer explicitement une source vérifiée ;
      une source nouvelle reste `pending` par défaut.
- [x] Télécharger les documents de découverte via le client anti-SSRF et traiter
      récursivement les index de sitemaps avec une profondeur bornée.
- [x] Ajouter la migration `0016` et une file de découverte dédupliquée par
      campagne/source, avec priorité, baux et trois tentatives persistantes.
- [x] Raccorder le worker à cette file avant le crawl, avec téléchargement hors
      transaction, finalisation atomique protégée par le bail, reprise des erreurs
      temporaires et journaux sans URL ni contenu.
- [x] Planifier automatiquement, à la fin atomique de chaque campagne manuelle ou
      récurrente, au plus 20 sources actives sitemap/feed par ordre déterministe ;
      leur reprise reste persistante et aucun téléchargement n'a lieu dans l'API.
- [x] Raccorder au crawl les résultats des seuls connecteurs qui l'autorisent
      explicitement, avec revalidation de chaque URL et refus par défaut.
- [x] Évaluer Common Crawl dans `docs/COMMON_CRAWL_EVALUATION.md` et reporter son
      intégration : l'index d'URL n'est pas un moteur d'identité, son API publique
      est fortement limitée et une chaîne WARC sûre dépasserait ce périmètre.

La phase D est **terminée pour son périmètre d'implémentation** : toutes les
entrées prévues sont filtrées, bornées, persistantes et couvertes sans accès
réseau réel. Common Crawl a été évalué mais volontairement non intégré selon les
critères documentés ; ce report n'est pas présenté comme une fonctionnalité.

## Phase E — plateformes

- [x] Ajouter la migration additive `0017` et les contrôles normalisés par
      campagne, avec contrainte unique, provenance du connecteur et isolation par
      propriétaire.
- [x] Finaliser atomiquement les plateformes réellement contrôlées et celles sans
      méthode publique, sans fabriquer de résultat pour une plateforme simplement
      non sélectionnée.
- [x] Exposer au propriétaire `GET /scans/{id}/platform-checks` avec une note
      rappelant que les statuts négatifs ne prouvent pas l'absence de compte.
- [ ] Implémenter les connecteurs prioritaires supplémentaires uniquement lorsque
      leur méthode publique et autorisée est stable, testable et minimisée.
- [x] Ajouter Bluesky par résolution exacte de handle via l'API publique AT
      Protocol, sans nom ni e-mail, avec dix requêtes maximales, quota persistant,
      refus des redirections et tests par transport simulé.
- [x] Évaluer Gravatar, Docker Hub et npm puis reporter leur intégration plutôt que
      d'utiliser une API à clé non configurée, authentifiée, héritée ou non documentée.
- [x] Intégrer les contrôles de plateformes à la vue utilisateur avec chargement
      à la demande et note méthodologique, puis exposer dernier contrôle et erreur
      dans le catalogue administratif, en français et en anglais.

La phase E reste **en cours** : le contrat persistant, le moteur systématique,
Bluesky et les vues utilisateur/administrative sont en place. L'ajout éventuel
d'autres connecteurs prioritaires exige encore une méthode officielle adaptée.

## Phase F — analyse et corrélation

- [x] Alimenter atomiquement `Evidence`, `EvidenceMatch` et
      `IdentityCorrelation` lors du crawl de la page racine d'un résultat de
      connecteur, avec extraits bornés, provenance versionnée et critères hachés
      par propriétaire.
- [x] Limiter la première analyse aux correspondances exactes normalisées,
      conserver séparément pertinence et attribution, plafonner le nom seul et
      ne jamais attribuer implicitement une page secondaire.
- [x] Ajouter la revue utilisateur privée (confirmation, rejet, incertitude,
      correction d'attribution et exclusion d'un homonyme) et sa réutilisation
      strictement limitée au même propriétaire.
- [x] Ajouter une classification contextuelle lexicale bornée, signaler le nom
      seul et les homonymes possibles, dédupliquer les preuves par empreinte de
      contenu et n'autoriser le nom approximatif qu'avec corroboration.
- [ ] Étendre prudemment la détection des doublons, contradictions et
      entités nommées au-delà de ces heuristiques contrôlées, avec leurs
      explications et tests.

La phase F est **en cours** : l'analyse exacte des pages racines est raccordée à
la transaction de crawl et la revue humaine privée est exposée avec réutilisation
traçable. Les rapprochements approximatifs et l'analyse contextuelle sont
implémentés dans une première forme bornée ; une analyse d'entités plus riche
reste à réaliser.

## Phase G — interface de revue

- [x] Intégrer aux résultats la consultation à la demande des preuves, les deux
      scores distincts, les indicateurs de prudence et les décisions confirmer,
      rejeter, incertain ou homonyme.
- [x] Permettre la correction vers un profil appartenant au compte et l'ajout
      explicitement consenti d'une URL aux profils confirmés, avec traductions
      françaises et anglaises et test de composant hermétique.
- [x] Réaliser l'audit statique et automatisé de toutes les vues dans
      `docs/UI_AUDIT.md`, corriger le nom accessible des panneaux de preuves et
      inventorier explicitement la recette visuelle restante.
- [x] Revalider le parcours E2E synthétique sur Chromium avec bascule du viewport
      bureau vers mobile, y compris connecteur non configuré, scan simulé,
      validation, export et sauvegarde, sans accès à des données réelles.
- [x] Corriger la navigation mobile révélée par la recette : le tableau de bord
      est désormais accessible comme sur bureau, avec test de composant adapté.
- [ ] Poursuivre l'audit responsive et ergonomique global des autres vues prévu
      par une recette visuelle multi-largeurs avant de déclarer la phase G terminée.

La phase G est **en cours** : la revue des preuves est intégrée, mais l'audit
complet de toutes les pages reste un chantier distinct.

## Évolution — recherche SearXNG auto-hébergée

- [x] Connecteur SearXNG local : API JSON via POST, maximum cinq requêtes par
      scan, plafond persistant partagé de cinq requêtes/minute, timeout, refus des
      redirections, déduplication et filtrage des URL de destination locales.
- [x] Minimisation : seuls nom complet et pseudonymes sont transmis ; e-mails,
      variantes, domaines et mots-clés sont exclus. Confirmation demandée dans
      l'interface et exigée côté API pour scans et planifications.
- [x] Configuration des endpoints restreinte à loopback natif ou au nom de service
      Compose, afin de ne pas créer un canal SSRF configuré par l'utilisateur.
- [x] Déploiements : image SearXNG versionnée, instance Compose sur un réseau
      privé séparé sans port publié et installation native optionnelle si Docker
      Compose est présent, publiée uniquement sur loopback.
- [x] Tests hermétiques du connecteur, de la configuration, du consentement API,
      du déploiement et de la planification ; suite backend complète : 136 réussis,
      1 PostgreSQL opt-in ignoré. Ruff et mypy passent ; frontend : 24 tests,
      build TypeScript/Vite, ESLint et Prettier passent.
- [x] Déployer sur DEB13-TEST après sauvegarde applicative privée
      `/var/backups/digitalfootprint/pre-searxng-20261020.tar.gz` (mode `0600`).
      Installer Docker Compose depuis les paquets Debian puis envoyer une archive
      source sans `.env`, base, venv ni `node_modules`; SHA-256 contrôlé avant
      exécution de `scripts/update-native.sh`. Les données et la configuration
      existantes ont été conservées.
- [x] Vérifier sur la VM Docker `26.1.5+dfsg1`, Compose `2.26.1-4`, le conteneur
      SearXNG `2026.10.19-81371861f` sain, les cinq services (Docker, SearXNG,
      web, worker et nginx) actifs, et HTTP 200 sur `/health` et SearXNG loopback.
- [x] Une seule recherche synthétique sans profil personnel : HTTP 200, JSON valide,
      52 résultats reçus. Cela valide le chemin de requête et l’agrégation observée,
      pas l’exactitude ni la disponibilité durable des moteurs amont. Aucun résultat
      individuel n’a été conservé dans ce compte-rendu.
- [x] Finaliser le compte-rendu documenté et la procédure de prérequis Debian 13.

## Évolution — recherche globale et diagnostic DEB13-TEST

- [x] Analyse des connecteurs et de la tentative Brave sur la VM en lecture seule.
      Le scan le plus récent utilisait Brave, a échoué après trois tentatives avec
      `connector_error` ; aucune clé Brave n'existe dans le coffre ou la variable
      d'environnement. Les journaux Web confirment la mise en file HTTP 201 ; le
      journal worker ne consigne pas l'erreur fournisseur elle-même.
- [x] Indicateur `ready` du catalogue connecteurs ; refuse côté API les scans
      demandant une clé absente, sans révéler de secret.
- [x] Bouton « Recherche globale » qui sélectionne les sources activées, prêtes et
      pertinentes selon les types d'identifiants du profil ; exige un moteur
      généraliste prêt et garde la confirmation Brave. Aucun nouveau fournisseur
      généraliste n'est ajouté par cette évolution.
- [x] Consentement Brave actualisé avec l'information de conservation des journaux
      de requêtes jusqu'à 90 jours selon la notice consultée le 20 octobre 2026.
- [x] Worker recharge le registre et les secrets depuis le coffre avant chaque
      scan, permettant de configurer un fournisseur depuis l'interface sans
      redémarrer manuellement son service ; tests du daemon mis à jour.
- [x] Tests backend : 126 passés, 1 test PostgreSQL opt-in ignoré ; Ruff et mypy
      strict réussis. Frontend : 24 tests, build TypeScript/Vite, ESLint et Prettier
      réussis.
- [x] Déployer le code source sur DEB13-TEST après sauvegarde applicative privée,
      transfert d'une archive excluant configuration, base et dépendances, et
      vérification de son SHA-256. La mise à jour native a reconstruit le frontend,
      appliqué les migrations et redémarré les services.
- [x] Corriger le défaut du scheduler SQLite : les dates naïves rechargées depuis
      SQLite sont normalisées en UTC avant comparaison. Après déploiement, les
      services web, worker et nginx sont actifs, le worker n'a aucun redémarrage
      (`NRestarts=0`) et `/health` répond `{"status":"ok"}`.
- [x] Suite backend complète relancée avec `-W error::ResourceWarning` : 126 tests
      réussis et 1 test PostgreSQL opt-in ignoré. Le frontend avait également passé
      ses 24 tests et ses contrôles de build, ESLint et Prettier avant ce déploiement.
- [x] SearXNG est désormais disponible sur la VM pour les prochains scans. Aucun
      scan avec le profil utilisateur n'a été lancé pendant le déploiement ; les
      requêtes de profil devront être explicitement confirmées dans l'interface.
- [ ] Un scan avec le profil via Brave reste bloqué jusqu'à la configuration
      d'une clé Brave dans l'interface d'administration. La VM ne possède pas de
      clé Brave configurée ; aucune donnée du profil n'a donc été envoyée. Après
      configuration, l'utilisateur doit lancer « Recherche globale » et confirmer
      explicitement l'envoi au fournisseur.

## Phase 0 — analyse

- [x] Inspection du dépôt (initialement vide) et de Git.
- [x] Inventaire local puis installation vérifiée : Python 3.13.5, Node.js
      20.19.2, npm 9.2.0, Docker 29.9.0, Compose 5.6.0 et PostgreSQL 17.11.
- [x] Architecture, modèle initial, stratégie de sécurité et versions documentés.
- [x] Structure initiale, AGENTS.md et documentation créés.
- [ ] Installer les outils manquants et exécuter une matrice Debian 13 réelle.

La phase 0 reste **partiellement validée** : les décisions et fichiers sont présents,
mais la compatibilité d'installation Debian ne pourra être vérifiée qu'en phase 5.

## Phase 1 — socle backend

- [x] Configuration typée par environnement.
- [x] Modèles SQLAlchemy SQLite/PostgreSQL et migration initiale Alembic.
- [x] Bootstrap administrateur, Argon2id, sessions hachées, CSRF, restauration
      du jeton CSRF après rechargement et déconnexion.
- [x] CRUD de profils avec validation, propriété et audit minimal.
- [x] Tests API préparés pour santé, authentification et profils.
- [x] Dépendances installées dans `backend/.venv` ; 126 tests collectés, dont
      125 réussis et un test PostgreSQL opt-in ignoré faute de base configurée dans
      la dernière exécution complète.
- [x] Ruff et mypy strict passent ; migration SQLite testée en upgrade/downgrade/upgrade.
- [x] Migrations SQLite et PostgreSQL 17 validées en montée, descente complète
      puis remontée jusqu'à `0011 (head)`. Le test PostgreSQL temporaire a révélé
      puis permis de corriger les types ENUM résiduels de la migration `0001`.
- [x] Rotation et expiration opportuniste des sessions ; isolation multi-utilisateur testée.
- [x] API scans/résultats, annulation et permissions par propriétaire.

Phase 1 **terminée pour le périmètre du socle** : tests, Ruff, mypy strict,
OpenAPI et cycles de migrations SQLite/PostgreSQL sont validés. Le démarrage
Compose PostgreSQL et les sauvegardes/restaurations depuis son backend ont aussi
été testés réellement.

## Phase 2 — moteur OSINT

- [x] Contrat et registre de connecteurs typés.
- [x] Connecteur simulé hermétique réservé aux tests.
- [x] Normalisation d'URL, déduplication intra-scan et score déterministe expliqué.
- [x] Runner initial : états persistés, progression et résultats.
- [x] Acquisition atomique par bail, reprise des baux expirés, trois tentatives et
      backoff persistant ; worker séparé intégré à systemd et Compose.
- [x] Timeouts fournisseur, reprises persistantes avec backoff exponentiel et
      jitter, rate limiting global en base et suspension jusqu'au reset de quota GitHub.
- [x] Validation SSRF des schémas/ports/adresses, de toutes les réponses DNS et de
      chaque redirection, avec retrait d'Authorization entre origines et tests dédiés.
- [x] Connexion réseau épinglée à l'adresse DNS validée, avec conservation du nom
      d'hôte pour `Host` et SNI/TLS ; redirections et rebinding couverts par tests.
- [x] Connecteur GitHub réel via API officielle, consultation exacte de profils,
      jeton facultatif et tests hermétiques par transport simulé.
- [x] Connecteur GitLab réel via point de terminaison officiel de statut public,
      pseudonymes exacts seulement, réponses minimisées, limitation persistante et
      tests hermétiques par transport simulé.
- [x] Connecteur Wayback/CDX limité aux domaines et sites connus du profil,
      normalisation/filtrage des captures, quota persistant et tests hermétiques.
- [x] Connecteur Brave Search officiel facultatif : noms et pseudonymes seulement,
      confirmation explicite, clé API par coffre chiffré, plafond et reprise de quota,
      résultats validés/minimisés et tests par transport HTTP simulé ; avertissements
      de divulgation et de tarification documentés dans README, configuration et guide.
- [x] Catalogue authentifié des connecteurs, validation avant mise en file et
      synthèse par utilisateur (santé, dernière exécution, résultats et erreurs).

## État des phases

- Phases 1 à 4 : fonctionnalités principales implémentées ; vérifications ouvertes
  et limites connues restent listées ci-dessous.
- Phase 5 : les deux variantes Compose SQLite/PostgreSQL viennent d'être
  reconstruites et démarrées avec succès ; l'installation native réelle sur
  l'hôte reste à effectuer.
- Phase 6 : CI et documentation PDF en place ; audit final et exécution sur de vrais
  runners restent à faire.

## Évolution — Sensitive Data Exposure Monitor

- [x] Analyse d'impact et architecture indépendante du moteur OSINT généraliste.
- [x] Validation locale NIR (format et clé), PAN/Luhn, IBAN, téléphone et adresse.
- [x] Masquage et empreinte HMAC ; aucune persistance de valeur brute.
- [x] Descripteurs, consentements, contrôles, constatations et alertes.
- [x] Contrat fournisseur sensible et service de correspondance locale.
- [x] API authentifiée avec CSRF, propriété et suppression.
- [x] Migrations `0002` et `0003` validées sur SQLite et PostgreSQL 17 ; l'index
      de rétention a été contrôlé sur les deux moteurs.
- [x] Tests de validation, masquage, non-fuite, accès et erreur fournisseur.
- [x] Page React/TypeScript « Sécurité > Exposition des données sensibles » responsive.
- [x] Dépendances npm installées ; TypeScript strict, ESLint, Prettier, 14 tests
      Vitest, un parcours Playwright et build Vite de production validés.
- [x] Navigation fonctionnelle, tableau de bord, création de profils, lancement et
      annulation des scans GitHub, historique et validation des résultats dans React.
- [x] Rapports synthétiques/détaillés CSV, JSON, XLSX, HTML et PDF avec contrôle
      d'accès, audit, historique minimisé, neutralisation des formules et contenus
      distants échappés ; les fichiers générés ne sont pas conservés côté serveur.
- [x] Surveillance quotidienne, hebdomadaire ou mensuelle persistante, création
      atomique des scans échus, pause/reprise/suppression et interface responsive.
- [x] Comparaison déterministe de deux scans terminés : nouvelles mentions,
      mentions connues, modifications, éléments non revérifiés et faux positifs
      exclus. Une absence n'est jamais assimilée à une suppression.
- [x] Registre local des demandes de suppression avec association facultative à
      une mention, statuts, dates, notes, audit et modèle de courrier sans envoi
      automatique ; migration `0008` validée sur SQLite.
- [x] Notifications internes minimisées après comparaison avec le scan précédent,
      préférence d’activation, historique et lecture ; migration `0009` validée en
      montée, rétrogradation et remontée sur SQLite.
- [x] Recherche de résultats paginée côté serveur avec texte, source, domaine,
      statut, dates et liste blanche de tris ; filtres raccordés à l’interface.
- [x] Édition de tous les critères d’un profil depuis l’interface et suppression
      protégée par une confirmation explicite.
- [x] Tableau de bord fondé sur des agrégats complets par propriétaire et graphique
      accessible de l’évolution quotidienne sur trente jours.
- [x] Vue d’administration : version, paramètres non secrets, santé des connecteurs
      et journal d’audit paginé avec détails filtrés par liste blanche.
- [x] Coffre administrable des jetons connecteurs avec AES-256-GCM, clés maître
      versionnées hors base, rotation transactionnelle, suppression, CSRF et audit ;
      migration `0010` validée en montée, rétrogradation et remontée sur SQLite.
- [x] Activation persistante des connecteurs : refus des nouveaux travaux,
      suspension des planifications et annulation des scans actifs à la désactivation ;
      migration `0011` validée en montée, rétrogradation et remontée sur SQLite.
- [x] Sauvegarde administrable sans chemin utilisateur : archive temporaire
      privée, exécution sérialisée, CSRF, audit, absence de cache et suppression après
      transfert. Le parcours Playwright vérifie une véritable archive SQLite gzip.
- [x] Pipelines GitHub Actions et GitLab CI : qualité, tests, couverture,
      migrations SQLite et PostgreSQL, audits npm et pip-audit, artefact frontend, images Docker et
      intégration Compose, sans publication automatique. Le parcours E2E hermétique
      Playwright est intégré aux deux pipelines. YAML et commandes validés localement.
- [x] Images backend/frontend reconstruites après les évolutions récentes, avec
      `cryptography 50.0.2` ; les quatre services Compose SQLite sont devenus sains,
      les migrations jusqu’à `0011` ont été appliquées, le proxy a répondu, les
      utilisateurs non-root ont été contrôlés puis les ressources éphémères supprimées.
- [x] Audit Python avec `pip-audit 2.10.1` : retrait de `python-multipart 0.0.20`,
      inutilisé et signalé vulnérable. Audit du projet sans vulnérabilité connue,
      tests réussis après désinstallation et image backend reconstruite sans ce paquet.
- [x] Parcours bootstrap/connexion, restauration de session, CSRF en mémoire et
      déconnexion intégré à l'interface.
- [x] Constatations et alertes privées consultables ; niveau de risque,
      recommandation masquée et prise en compte auditée depuis l'interface.
- [x] Purge bornée et idempotente des descripteurs expirés, historique préservé,
      commande dédiée et timer systemd quotidien pour l'installation native ; unités
      validées dans une racine systemd temporaire.
- [x] Images backend/frontend multi-stage non-root, Compose SQLite persistant,
      variante PostgreSQL isolée, healthchecks et maintenance conteneurisée.
- [x] Build réel des images et démarrage SQLite validés ; proxy, en-têtes de
      sécurité, migrations, utilisateurs non-root et persistance après redémarrage
      contrôlés. Le volume de validation est conservé et les conteneurs sont arrêtés.
- [x] Variante PostgreSQL 17 démarrée réellement avec identifiants synthétiques :
      quatre services sains, migration `0003`, aucun port PostgreSQL publié, arrêt
      propre et volume de validation conservé.
- [x] Refus des clés d'exemple en environnement de production, couvert par test
      unitaire et vérifié directement dans l'image backend.
- [x] Installateur natif Debian 13 idempotent pour les fichiers de configuration,
      compte sans shell, venv, build frontend, migrations, Web/Nginx et rétention.
      Bash, unités systemd et Nginx sont validés sans mutation privilégiée de l'hôte.
- [x] Mise à jour native réutilisant l'installateur idempotent et conservant le
      fichier de configuration existant.
- [x] Sauvegarde/restauration SQLite et PostgreSQL avec archives privées, manifeste,
      contrôle SHA-256, confirmation destructive et gestion du service Web.
- [x] Désinstallation native avec conservation des données par défaut et purge
      séparée nécessitant une confirmation explicite.
- [ ] Revue juridique et contractuelle avant tout fournisseur externe réel.
- [x] Tests hermétiques des cinq formats de rapport et de leurs protections.
- [x] Sauvegarde/restauration PostgreSQL réellement exercée avec `pg_dump` et
      `pg_restore` sur PostgreSQL 17.11 temporaire : restauration contrôlée d'une
      valeur synthétique après modification. Ce test a découvert puis corrigé le
      passage erroné de l'URL dans `PGDATABASE` et l'absence de `--dbname` à
      `pg_restore` ; un test hermétique vérifie l'environnement et l'absence du mot
      de passe dans les arguments. Le test de round-trip est maintenant opt-in dans
      pytest et raccordé aux jobs PostgreSQL GitHub Actions/GitLab CI ; les 5 tests
      de sauvegarde/restauration réussissent sur le cluster PostgreSQL temporaire.

## Travail restant avant la première version

- [x] Valider les migrations `0001–0011` sur PostgreSQL 17.11 : cluster temporaire
      non-TCP dans `/tmp`, montée complète, descente à `base`, remontée et contrôle
      de 20 tables avec `alembic_version=0011`. Le downgrade a révélé puis corrigé
      les types ENUM laissés par `0001`.
- [x] Fermer la fenêtre de DNS rebinding en liant la connexion HTTP à l’adresse
      résolue et validée, sans casser TLS ni la vérification du nom d’hôte.
- [x] Compléter l’administration avec l’activation des connecteurs, le coffre
      chiffré avec rotation et l’orchestration contrôlée des sauvegardes.
- [x] Couche FR/EN pour la navigation, l’écran de connexion, les contrôles communs
      et les pages métier principales ; le français reste la langue par défaut et la
      préférence est locale au navigateur. Les contenus issus des sources et messages
      externes ne sont pas traduits artificiellement.
- [x] Ajouter Playwright et le parcours E2E authentification → profil → scan
      simulé traité par le worker → résultat confirmé → rapport CSV, sans accès
      Internet et avec base temporaire migrée.
- [x] Rejouer ce parcours le 17 octobre : après correction d'un sélecteur
      accessible devenu obsolète dans le test, le scénario Chromium passe en 10,6 s.
      Il vérifie maintenant également que le refus du consentement Brave n'envoie
      aucune requête de scan ; scénario complet repassé après correction de migration,
      en 10,5 s.
- [x] Tests du worker persistant sur exécution réussie et erreur fournisseur :
      les résultats sont persistés et les erreurs sont replanifiées avec un code
      générique. Bail exclusif et reprise après expiration déjà couverts.
- [x] Audits de dépendances le 17 octobre : `pip-audit --strict .` sans
      vulnérabilité connue et `npm audit --audit-level=moderate` sans vulnérabilité.
      La couverture backend précédemment mesurée était de 89 % ; la dernière suite
      complète comprend 126 tests collectés (125 réussis, un test d'intégration
      PostgreSQL ignoré par défaut).
- [x] Répétition des audits de dépendances pendant la revue finale :
      `pip-audit --strict .` ne trouve aucune vulnérabilité connue et
      `npm audit --audit-level=moderate` trouve zéro vulnérabilité. Le premier essai pip-audit
      en sandbox n'a pas pu installer son environnement d'inspection ; le même audit
      a réussi avec l'accès réseau autorisé.
- [x] Arrêt gracieux du worker renforcé : les signaux interrompent l'attente du
      rate limiter, et le scan acquis est replanifié au lieu d'attendre l'expiration
      du bail. Deux tests hermétiques couvrent l'interruption et la reprise.
- [x] Correction du message de sauvegarde native : l'archive n'étant pas chiffrée
      par l'application, le script demande explicitement de la chiffrer avant transfert.
- [x] Validation syntaxique des deux configurations Compose (PostgreSQL avec
      variables synthétiques et fichiers SQLite/PostgreSQL fusionnés) et `bash -n`
      des scripts natifs.
- [x] Ajout d'un job PostgreSQL de cycle montée/descente/remontée dans GitHub
      Actions et GitLab CI pour prévenir la régression des types ENUM.
- [ ] Exécuter les pipelines sur de vrais runners GitHub et GitLab après création
      d'un commit et configuration d'un remote ; à ce jour, le dépôt local n'a aucun
      commit ni remote. Aucun push n'a été effectué.
- [x] Générer les PDF des guides utilisateur et administrateur depuis Markdown,
      avec tests hors réseau, commande dédiée et artefacts CI temporaires.
- [x] Reconstruire et lancer les variantes Compose SQLite et PostgreSQL : tous les
      services sont sains, migrations `0011`, interface/endpoint servis avec
      en-têtes de sécurité ; PostgreSQL n'a aucun port hôte publié. Le test a révélé
      l'absence de `pg_dump`/`pg_restore` dans l'image backend ; `postgresql-client`
      17 a été ajouté, puis un round-trip de sauvegarde/restauration synthétique a
      réussi depuis le backend Compose. Les conteneurs et volumes temporaires ont
      été supprimés après vérification. L'image a ensuite été reconstruite avec
      l'installation non interactive, et les deux utilitaires ont été vérifiés
      dans un conteneur sans réseau sous l'UID applicatif non-root `10001`.
- [ ] Tester l’installation native complète Debian 13 sur une instance propre ;
      l'installation réelle sur l'hôte n'a pas été lancée pour éviter des changements
      système privilégiés.
- [ ] Revue juridique et contractuelle Brave avant activation réelle ; vérifier
      périodiquement les tarifs et conditions du fournisseur. Bing et HIBP restent
      à étudier. Évaluer séparément les licences et comportements de Sherlock et
      Maigret avant toute intégration.
- [ ] Effectuer l’audit final : dépendances, couverture, accessibilité, menace,
      restauration complète, arrêt/reprise des workers et préparation de la version.
- [x] Fermeture explicite des connexions SQLite dans le test de sauvegarde ; la
      suite passe sans avertissement avec `-W error::ResourceWarning`.

## Décisions et problèmes

- Monolithe modulaire et file en base choisis pour ne pas imposer Redis.
- SQLite en mode personnel ; PostgreSQL pour concurrence et plusieurs workers.
- Les dépendances backend et frontend ont été installées après autorisation.
- Starlette 1.8 utilise désormais `httpx2` pour son client de test. Sous Python
  3.13, le backend asyncio standard se bloquait dans le portail de test ; les tests
  emploient `uvloop`, déjà installé par `uvicorn[standard]`.
- Les versions Vite 7 et TypeScript 5.9 ont été retenues pour respecter les plages
  de compatibilité de Tailwind CSS 4 et typescript-eslint 8.
- L'audit npm final ne signale aucune vulnérabilité après mise à jour de Vite,
  React Router, typescript-eslint et Vitest. npm 9 a nécessité sa résolution de
  pairs héritée pour les pairs optionnels de Vitest 4 ; les pairs utilisés sont
  tous déclarés directement et le lockfile a été régénéré.
- Les migrations PostgreSQL `0001–0011` ont été vérifiées avec PostgreSQL 17.11
  temporaire sans écoute réseau. Compose SQLite et PostgreSQL ont été reconstruits
  et validés dans des projets éphémères ; leurs conteneurs et volumes de test ont
  été retirés. Aucun droit de la machine hôte ni installation native n'a été modifié.
- La couche de traduction initiale est une solution locale typée sans dépendance
  runtime ; elle couvre la navigation, l’écran d’authentification, les contrôles
  communs et toutes les pages principales de l’application.
  Le modèle de courrier RGPD, les contenus de notifications, recommandations et
  messages d’erreur externes restent dans leur langue de génération (français
  actuellement) ; certaines valeurs techniques et lignes d’audit ne sont pas
  traduites.
- Vérifications frontend après cette évolution : 23 tests Vitest, lint ESLint,
  contrôle Prettier et build TypeScript/Vite réussis.
