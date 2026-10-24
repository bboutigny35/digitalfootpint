# Installation Docker Compose

## Prérequis et configuration

Docker Engine et le plugin Compose sont requis. Le seul port publié est lié à
`127.0.0.1` par défaut ; PostgreSQL et FastAPI restent sur des réseaux Docker sans
port hôte.

```bash
cp .env.example .env
python3 -c 'import secrets; print(secrets.token_urlsafe(48))'
```

Placez la valeur générée dans `DIGITALFOOTPRINT_SECRET_KEY`. L'application refuse
les clés d'exemple en mode production. Protégez ensuite le fichier :

```bash
chmod 600 .env
```

## Démarrage avec SQLite

```bash
docker compose build
docker compose up -d --wait
docker compose ps
```

L'interface est disponible sur `http://127.0.0.1:8080`. Le volume nommé
`digitalfootprint_app-data` contient la base. Les migrations sont appliquées avant
le démarrage de FastAPI. Le conteneur `retention` purge quotidiennement les
descripteurs sensibles expirés ; son intervalle est réglable entre 300 et 604800
secondes.

```bash
docker compose logs --tail=100 backend retention
docker compose stop
docker compose start
docker compose down          # conserve les volumes
```

### Recherche SearXNG

L'instance SearXNG est une option explicite via un overlay ; sans celui-ci le
connecteur reste indisponible et aucun service de recherche supplémentaire ne
démarre. Générez un secret aléatoire sans le publier, placez-le comme
`SEARXNG_SECRET` dans `.env`, protégez le fichier (`chmod 600 .env`), puis utilisez
le même overlay pour toutes les opérations Compose de la pile :

```bash
python3 -c 'import secrets; print(secrets.token_urlsafe(48))'
docker compose -f compose.yaml -f compose.searxng.yaml up -d --build --wait
docker compose -f compose.yaml -f compose.searxng.yaml ps
```

SearXNG n'a aucun port publié et n'est joignable que depuis le réseau interne de
l'application. L'API JSON est activée. Le backend n'envoie que noms et
pseudonymes après confirmation de l'utilisateur ; SearXNG relaie ces termes aux
moteurs activés. La configuration ne supprime pas les quotas, CAPTCHA ou
restrictions appliqués par les moteurs amont. Arrêtez la pile avec le même ensemble
de fichiers `-f`. Le volume `searxng-cache` est conservé lors de `down`.

N'utilisez `docker compose down --volumes` que pour supprimer explicitement toutes
les données de cette pile.

## Variante PostgreSQL

Définissez `POSTGRES_PASSWORD` puis construisez une URL dont le mot de passe est
encodé pour une URL :

```bash
read -rsp "Mot de passe PostgreSQL : " DB_PASSWORD; echo
ENCODED_PASSWORD="$(DB_PASSWORD="$DB_PASSWORD" python3 -c 'import os, urllib.parse; print(urllib.parse.quote(os.environ["DB_PASSWORD"], safe=""))')"
printf 'COMPOSE_POSTGRES_DATABASE_URL=postgresql+psycopg://digitalfootprint:%s@postgres:5432/digitalfootprint\n' "$ENCODED_PASSWORD"
unset DB_PASSWORD ENCODED_PASSWORD
```

Copiez la ligne affichée dans `.env`, sans guillemets autour de l'URL, puis lancez :

```bash
docker compose -f compose.yaml -f compose.postgres.yaml up -d --build --wait
docker compose -f compose.yaml -f compose.postgres.yaml ps
```

Le port PostgreSQL n'est pas publié. Le réseau `database` est marqué interne ; le
backend conserve un réseau applicatif distinct pour le proxy et les futurs appels
sortants des connecteurs autorisés.
L'image runtime du backend contient le client PostgreSQL 17 nécessaire aux archives
créées et restaurées depuis l'administration ; aucune installation cliente sur
l'hôte n'est requise pour ces fonctions.

## Mise à jour

Sauvegardez d'abord les données, puis :

```bash
docker compose build --pull
docker compose up -d --wait
docker compose ps
```

Pour PostgreSQL, ajoutez `-f compose.postgres.yaml` à chaque commande. Aucune image
n'est publiée automatiquement par le projet.

## Sauvegarde et restauration

Pour SQLite, arrêtez la pile avant de copier la base afin d'obtenir une image
cohérente :

```bash
mkdir -p backups
chmod 700 backups
docker compose stop
docker run --rm -v digitalfootprint_app-data:/data:ro -v "$PWD/backups":/backup alpine:3.22 sh -c 'cd /data && tar czf /backup/digitalfootprint-sqlite.tgz digitalfootprint.db'
docker compose start
```

Pour PostgreSQL :

```bash
docker compose -f compose.yaml -f compose.postgres.yaml exec -T postgres \
  pg_dump -U digitalfootprint -d digitalfootprint -Fc > backups/digitalfootprint.dump
chmod 600 backups/digitalfootprint.dump
```

Une restauration remplace des données : consultez
[la procédure dédiée](../administration/backup-restore.md) et confirmez la cible
avant toute commande de restauration.

## Exposition HTTPS

La liaison locale est volontaire. Pour une exposition réseau, placez un reverse
proxy HTTPS devant `127.0.0.1:8080`, définissez `DIGITALFOOTPRINT_COOKIE_SECURE=true`
et adaptez les origines autorisées. Ne remplacez pas la liaison par `0.0.0.0` sans
contrôle d'accès réseau et TLS.

## Limites de ressources

Compose ne fixe pas de limites universelles par défaut car les besoins dépendent
du nombre de scans. Une base de départ raisonnable est 768 Mio/1 CPU pour le
backend, 256 Mio/0,5 CPU pour la rétention, 128 Mio/0,5 CPU pour Nginx et 1 Gio/1
CPU pour PostgreSQL. Appliquez ces limites dans un fichier d'override adapté à
votre hôte et surveillez les erreurs de mémoire avant de les réduire.
