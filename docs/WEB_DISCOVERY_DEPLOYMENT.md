# Déploiement de la découverte Web

La découverte est incluse dans le backend et le worker DigitalFootprint. Elle ne
nécessite ni Redis ni service supplémentaire, sauf SearXNG lorsqu'il est choisi
comme moteur généraliste local.

## Docker Compose

Suivre [`installation/docker.md`](installation/docker.md). La variante SQLite
utilise `compose.yaml`; PostgreSQL ajoute `compose.postgres.yaml`. Pour SearXNG,
ajouter `compose.searxng.yaml` et définir son secret selon le guide. SearXNG reste
sur un réseau privé et n'est pas publié sur l'hôte.

Le backend applique les migrations au démarrage. Les services worker et rétention
attendent son healthcheck et n'exécutent pas les migrations en parallèle. Après
démarrage :

```bash
docker compose ps
curl --fail http://127.0.0.1:8080/health
```

## Debian 13 natif

Suivre [`installation/debian13.md`](installation/debian13.md). L'installateur crée
le compte sans shell, le venv, le frontend, les unités systemd et Nginx. Le script
de mise à jour conserve la configuration, installe le code, applique Alembic puis
redémarre les unités.

SearXNG natif est optionnel et publié uniquement sur loopback. Contrôler :

```bash
systemctl is-active digitalfootprint-web digitalfootprint-worker nginx
systemctl is-active digitalfootprint-retention.timer
curl --fail http://127.0.0.1:8080/health
```

## Ordre de mise à jour

1. Vérifier espace disque, base utilisée et état des unités.
2. Créer une sauvegarde privée selon
   [`administration/backup-restore.md`](administration/backup-restore.md).
3. Vérifier l'intégrité de l'artefact source et exclure `.env`, bases, venv,
   `node_modules` et résultats de tests.
4. Exécuter la mise à jour et confirmer la révision Alembic attendue.
5. Vérifier Web, worker, rétention, Nginx, SearXNG éventuel et healthchecks.
6. Contrôler que le worker ne redémarre pas en boucle et qu'aucun secret n'est
   apparu dans les journaux.

## Retour arrière

Une migration destructive n'est jamais implicite. Pour un incident applicatif,
arrêter les écritures, restaurer l'archive vérifiée et le code correspondant, puis
rejouer les sondes. Ne rétrograder Alembic qu'après vérification explicite de la
migration et sauvegarde. PostgreSQL exige `pg_restore`; SQLite utilise une copie
cohérente créée hors écriture.

La validation réalisée sur `DEB13-TEST` est consignée dans
[`TEST_ENVIRONMENT.md`](TEST_ENVIRONMENT.md).
