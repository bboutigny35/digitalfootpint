# Environnement de test DEB13-TEST

Dernier inventaire : 25 octobre 2026.

## Périmètre et précautions

`DEB13-TEST` est l'environnement prévu pour les validations Debian 13 natives et
Docker Compose. L'inventaire ci-dessous n'a réalisé aucune modification
destructive, aucune modification de l'hôte et aucune modification globale de
libvirt.

## Identité et état observés

| Élément                  | Valeur observée                           |
| ------------------------ | ----------------------------------------- |
| Nom libvirt              | `DEB13-TEST`                              |
| UUID                     | `1a144183-b50b-485b-be67-588c6ed11453`    |
| Hyperviseur              | QEMU/KVM via `qemu:///system`             |
| État au 25 octobre 2026  | active (`running`)                        |
| Type                     | HVM, domaine persistant                   |
| Processeurs virtuels     | 2                                         |
| Mémoire maximale/allouée | 2 Gio (`2097152 KiB`)                     |
| Sécurité libvirt         | AppArmor                                  |
| Démarrage automatique    | désactivé                                 |
| Sauvegarde gérée         | aucune                                    |
| Snapshots libvirt        | aucun listé                               |
| Interface                | virtio sur le réseau libvirt `default`    |
| Adresse MAC              | `52:54:00:41:03:18`                       |
| Adresse IPv4 invitée     | `192.168.122.25/24`                       |
| Réseau libvirt           | `default`, actif, persistant et autostart |

## Incident de démarrage résolu

Une tentative de démarrage autorisée de la VM a échoué avec :

```text
L'opération demandée n'est pas valide : le réseau 'default' n'est pas actif
```

Le réseau a ensuite été démarré par l'utilisateur. Une nouvelle vérification a
confirmé que la VM attendue, identifiée par le même UUID, est active. Aucun
changement global de libvirt n'a été effectué par l'agent.

## État vérifié dans l'invité

- Debian GNU/Linux 13.7 (`trixie`), noyau `6.12.113+deb13-amd64`.
- 2 processeurs virtuels, 1,9 Gio de mémoire et 1 Gio d'échange.
- Système de fichiers racine de 18 Gio : 6,8 Gio utilisés et 9,9 Gio disponibles.
- Route par défaut via le réseau libvirt et résolution DNS fonctionnelle.
- Accès HTTPS sortant vérifié par une réponse HTTP 200 de `deb.debian.org`.
- Docker `26.1.5+dfsg1`, Compose `2.26.1-4`, Python `3.13.5` et Node.js
  `20.19.2`.
- Services Web, worker, Nginx, SearXNG et Docker actifs.
- Sondes HTTP de l'application et de SearXNG sur loopback : HTTP 200.
- Conteneur SearXNG actif et sain au moment du contrôle.

## Validation de déploiement du 25 octobre 2026

- Une sauvegarde applicative privée a été créée avant modification dans
  `/var/backups/digitalfootprint/pre-phase-h-20261025.tar.gz`, en mode `0600`.
- L'archive source a exclu les secrets, bases et dépendances locales ; son
  empreinte SHA-256 a été vérifiée dans l'invité avant extraction.
- La mise à jour native a reconstruit le frontend et appliqué les migrations
  `0012` à `0019`. Alembic confirme `0019 (head)` sur la base SQLite installée.
- Les variantes Docker Compose SQLite et PostgreSQL ont chacune atteint leurs
  healthchecks et répondu sur `/health` depuis un port loopback secondaire.
- Le premier essai Compose a révélé qu'une URL SearXNG optionnelle vide était
  rejetée. Le validateur et son test ont été corrigés, puis la mise à jour native
  et les deux validations Compose ont réussi.
- Les projets Compose de validation, leurs réseaux et leurs volumes ont été
  supprimés. Le contrôle final ne montre que le conteneur SearXNG permanent.
- Après ces opérations, les six unités contrôlées sont actives, le worker indique
  `NRestarts=0`, l'application répond `{"status":"ok"}` et SearXNG HTTP 200.

Aucun profil personnel, e-mail, jeton fournisseur ou résultat OSINT réel n'a été
utilisé pendant cette validation.

## Installation propre et restauration du 25 octobre 2026

- Une nouvelle sauvegarde applicative et une archive séparée de configuration ont
  été créées en mode `0600`, puis leurs empreintes SHA-256 ont été contrôlées.
- La purge explicitement autorisée a supprimé application, configuration, état,
  frontend et compte système. Leur absence a été vérifiée avant réinstallation.
- L'installation native complète depuis cet état propre a recréé le compte sans
  shell, les répertoires privés, le frontend, la base à la migration `0019`, les
  unités systemd, Nginx et SearXNG. Toutes les sondes ont réussi.
- La configuration protégée et la sauvegarde ont ensuite été restaurées. Les
  empreintes différentes avant/après confirment le remplacement effectif de la
  base, sans publier son contenu.
- La recette a révélé que le wrapper de restauration n'arrêtait que le Web. Il
  arrête désormais aussi le worker et la rétention, puis rétablit uniquement les
  unités précédemment actives.
- Elle a également révélé un fichier SQLite en mode `0644` dans un répertoire
  `0700`. L'installation et la restauration imposent maintenant `0700` au
  répertoire et `0600` à la base ; le correctif a été exercé sur la VM.
- Après restauration et nouvelle exécution idempotente de l'installateur : six
  unités actives, worker à `NRestarts=0`, migration `0019 (head)`, application
  saine et SearXNG HTTP 200.

## Dernier état documenté antérieurement

Le journal de développement indique une validation le 20 octobre 2026 sur cette
VM. Le prompt fourni parle de `DEB-TEST`, tandis que le domaine libvirt réellement
présent se nomme `DEB13-TEST` ; l'UUID ci-dessus doit rester l'identifiant de
référence avant toute action :

- Debian 13 ;
- Docker `26.1.5+dfsg1` et Compose `2.26.1-4` ;
- SearXNG `2026.10.19-81371861f` ;
- services Docker, SearXNG, Web, worker et Nginx actifs ;
- réponses HTTP 200 pour l'application et SearXNG sur loopback ;
- sauvegarde applicative privée créée avant déploiement ;
- suite backend et contrôles frontend réussis.

Ces valeurs historiques concordent avec le nouvel inventaire, sans constituer une
garantie de disponibilité future.

## Possibilités de sauvegarde

La VM n'a actuellement aucun snapshot libvirt listé. Avant une modification de
déploiement, utiliser d'abord les sauvegardes applicatives documentées :

- SQLite : archive cohérente après arrêt des écritures ;
- PostgreSQL : `pg_dump` au format custom avec manifeste et SHA-256 ;
- configuration : archive privée excluant les secrets des comptes rendus et du
  dépôt.

Un snapshot de VM non destructif peut compléter ces sauvegardes si le stockage et
le format du disque le permettent, mais il ne les remplace pas. Sa faisabilité
doit être vérifiée une fois le domaine accessible.

## Contrôles à exécuter après autorisation réseau

1. Vérifier de nouveau l'UUID avant toute action.
2. Démarrer uniquement `DEB13-TEST` et attendre l'agent invité.
3. Relever `/etc/os-release`, noyau, CPU, mémoire et espace disque.
4. Relever interfaces, routes et résolveurs sans exposer de secrets.
5. Tester DNS, HTTPS sortant et horloge avec une cible publique neutre.
6. Contrôler Docker, Compose, PostgreSQL éventuel et versions applicatives.
7. Vérifier les services systemd et les healthchecks locaux.
8. Créer et vérifier une sauvegarde applicative avant mise à jour.
9. Exécuter migrations, tests backend/frontend et parcours E2E hermétique.
10. Vérifier redémarrage, reprise du worker et restauration synthétique.

Les sorties publiées dans la documentation doivent être minimisées : aucun mot
de passe, jeton, e-mail complet, donnée d'identité ou résultat OSINT individuel.
