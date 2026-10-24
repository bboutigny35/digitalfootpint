# Installation Debian 13

L'installateur cible exclusivement Debian 13. Il crée un compte
`digitalfootprint` sans shell, installe le backend sous `/opt/digitalfootprint`,
les fichiers Web publics sous `/var/www/digitalfootprint`, la configuration sous
`/etc/digitalfootprint` et les données SQLite sous `/var/lib/digitalfootprint`.
FastAPI écoute sur `127.0.0.1:8000` et Nginx sur
`127.0.0.1:8080`. Aucun pare-feu ni paramètre réseau n'est modifié.

## Installation

Depuis la racine du dépôt :

```bash
sudo ./scripts/install-native.sh
```

Le script vérifie Debian 13 et les versions de Python/Node, installe les paquets,
construit React, crée l'environnement virtuel, génère une clé d'installation lors
de la première exécution, applique les migrations puis active Web, Nginx et le
timer de rétention. Une configuration existante n'est jamais remplacée.

Si les paquets sont déjà gérés séparément :

```bash
sudo ./scripts/install-native.sh --skip-packages
```

Cette variante échoue si un prérequis manque. Vérifiez ensuite :

```bash
systemctl status digitalfootprint-web.service
systemctl status digitalfootprint-worker.service
systemctl status digitalfootprint-retention.timer
systemctl status digitalfootprint-searxng.service
curl --fail http://127.0.0.1:8080/health
journalctl -u digitalfootprint-web.service --since today
```

## Mise à jour

Placez-vous dans la nouvelle version du dépôt, puis lancez :

```bash
sudo ./scripts/update-native.sh
```

Le script conserve `/etc/digitalfootprint/digitalfootprint.env`, réinstalle le
backend et ses dépendances, reconstruit le frontend, applique les migrations et
redémarre les services. Réalisez une sauvegarde avant toute mise à jour de
production avec `scripts/backup.sh`.

## Désinstallation

La commande suivante retire l'application et les unités, mais conserve la
configuration et la base dans `/etc/digitalfootprint` et `/var/lib/digitalfootprint` :

```bash
sudo ./scripts/uninstall.sh --yes
```

Après une sauvegarde vérifiée, la suppression irréversible des données, de la
configuration et du compte système doit être demandée séparément :

```bash
sudo ./scripts/uninstall.sh --purge-data --yes
```

Le script ne désinstalle pas Nginx, Python, Node.js ou PostgreSQL, qui peuvent être
utilisés par d'autres applications.

Le fichier `/etc/digitalfootprint/digitalfootprint.env` est lisible uniquement par
root et le groupe applicatif. Pour utiliser PostgreSQL, modifiez
`DIGITALFOOTPRINT_DATABASE_URL`, puis appliquez les migrations sous le compte dédié
avant de redémarrer :

```bash
sudo -u digitalfootprint sh -c 'cd /opt/digitalfootprint/backend && .venv/bin/alembic upgrade head'
sudo systemctl restart digitalfootprint-web.service
```

### Recherche SearXNG locale

En mode natif, SearXNG est optionnel et utilise Docker Compose comme service isolé.
Sur Debian 13, installez les paquets Debian puis relancez la mise à jour native :

```bash
sudo apt update
sudo apt install docker.io docker-cli docker-compose
sudo systemctl enable --now docker
sudo ./scripts/update-native.sh
```

L'installation de Docker ajoute son service système et peut modifier la gestion
des règles réseau par défaut de Docker ; elle n'ajoute pas de port public pour
DigitalFootprint ou SearXNG. Vérifiez les règles de l'hôte avant cette étape si
celui-ci héberge d'autres services exposés.

Si Docker et le plugin Compose sont déjà installés, l'installateur configure aussi
SearXNG sur le port loopback `127.0.0.1:8888`, génère un secret indépendant dans
`/etc/digitalfootprint/searxng.env` (mode `0600`) et configure l'application. Le
conteneur est géré par `digitalfootprint-searxng.service`; les mises à jour de
l'application redémarrent le backend et le worker afin qu'ils chargent la
configuration. Si Docker Compose est absent, le reste de l'installation continue
et le connecteur reste indiqué « non configuré ».

```bash
systemctl status digitalfootprint-searxng.service
curl --fail http://127.0.0.1:8888/
```

Le port n'est pas exposé au réseau. Ne modifiez pas le bind pour le rendre public.
Les requêtes saisies dans l'interface sont relayées aux moteurs que SearXNG
active ; leur disponibilité et leurs politiques ne sont pas garanties.

Déploiement de référence vérifié le 20 octobre 2026 sur Debian 13 (VM
`DEB13-TEST`) : Docker `26.1.5+dfsg1`, Compose `2.26.1-4`, image SearXNG
`2026.10.19-81371861f`. Les sondes locales de l'application et du service de
recherche ont répondu HTTP 200 et les conteneurs/services étaient actifs. Une
requête de contrôle synthétique a retourné une réponse JSON avec 52 résultats ;
c'est un test de connectivité ponctuel, pas une garantie de couverture, de
pertinence ou de disponibilité des moteurs amont. Aucun profil ni donnée
personnelle n'a été envoyé durant ce test.

## Worker OSINT

Le service `digitalfootprint-worker.service` traite les scans indépendamment du
navigateur. Il utilise un bail persistant en base : un scan interrompu redevient
éligible après expiration du bail, avec trois tentatives et un backoff exponentiel.
Le connecteur GitHub officiel est le premier connecteur réel activé. Le faux
connecteur reste réservé aux tests et n'est pas enregistré par le worker.

Le timer de rétention est déjà fourni dans `deploy/systemd/`. Après installation
des fichiers par la future procédure automatisée, son activation explicite sera :

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now digitalfootprint-retention.timer
systemctl list-timers digitalfootprint-retention.timer
```

Ces commandes ne doivent pas être exécutées avant que le compte système, le fichier
`/etc/digitalfootprint/digitalfootprint.env` et l'environnement virtuel sous
`/opt/digitalfootprint/backend/.venv` existent.

## Exposition HTTPS

Conservez l'écoute locale et placez un reverse proxy TLS devant le port 8080.
Passez ensuite `DIGITALFOOTPRINT_COOKIE_SECURE=true` et adaptez
`DIGITALFOOTPRINT_CORS_ORIGINS`. L'installateur ne demande jamais l'ouverture d'un
port et ne modifie ni nftables, ni iptables, ni UFW.

## Limites de validation

La syntaxe du script, des unités systemd et de Nginx est validée automatiquement.
L'installation complète n'a pas été exécutée avec sudo sur la machine de
développement afin de ne pas modifier `/opt`, `/etc`, les comptes système ou les
services sans décision explicite de l'administrateur.
