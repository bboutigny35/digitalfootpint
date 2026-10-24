# Environnement de test DEB13-TEST

Dernier inventaire : 24 octobre 2026.

## Périmètre et précautions

`DEB13-TEST` est l'environnement prévu pour les validations Debian 13 natives et
Docker Compose. L'inventaire ci-dessous n'a réalisé aucune modification
destructive, aucune modification de l'hôte et aucune modification globale de
libvirt.

## Identité et état observés

| Élément | Valeur observée |
| --- | --- |
| Nom libvirt | `DEB13-TEST` |
| UUID | `1a144183-b50b-485b-be67-588c6ed11453` |
| Hyperviseur | QEMU/KVM via `qemu:///system` |
| État au 24 octobre 2026 | active (`running`) |
| Type | HVM, domaine persistant |
| Processeurs virtuels | 2 |
| Mémoire maximale/allouée | 2 Gio (`2097152 KiB`) |
| Sécurité libvirt | AppArmor |
| Démarrage automatique | désactivé |
| Sauvegarde gérée | aucune |
| Snapshots libvirt | aucun listé |
| Interface | virtio sur le réseau libvirt `default` |
| Adresse MAC | `52:54:00:41:03:18` |
| Adresse IPv4 invitée | `192.168.122.25/24` |
| Réseau libvirt | `default`, actif, persistant et autostart |

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
