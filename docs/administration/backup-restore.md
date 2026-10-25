# Sauvegarde et restauration

Les archives contiennent la base de données, donc des données personnelles. Elles
sont créées avec le mode `0600`, mais ne sont pas chiffrées par DigitalFootprint.
Stockez-les sur un volume chiffré, hors de la machine, avec une rétention limitée.
La configuration et ses clés secrètes ne sont volontairement pas incluses.
Sauvegardez séparément, dans un coffre sécurisé, les versions de
`DIGITALFOOTPRINT_CONNECTOR_SECRET_KEYS` encore utilisées. Sans elles, les jetons
connecteurs chiffrés présents dans une base restaurée sont irrécupérables.

## Sauvegarder

Un administrateur peut télécharger une archive depuis la page **Administration**.
Le serveur choisit lui-même un emplacement temporaire privé, sérialise les
créations concurrentes, transmet le fichier avec interdiction de cache puis le
supprime. Aucun chemin de fichier n'est accepté par l'API.

L'alternative native reste disponible :

```bash
sudo ./scripts/backup.sh /var/backups/digitalfootprint-2026-10-14.tar.gz
```

Le fichier de destination ne doit pas déjà exister. SQLite utilise son API de
sauvegarde en ligne. PostgreSQL utilise `pg_dump` au format personnalisé. L'URL de
connexion est décomposée en variables libpq de l'environnement du sous-processus ;
le nom de la base seul est fourni à `pg_restore`. Le mot de passe n'est jamais
affiché ni placé dans les arguments. L'archive contient un manifeste et une somme
SHA-256.

## Restaurer

La restauration n'est jamais proposée par l'interface Web.

Commencez par sauvegarder l'état actuel, puis fournissez la confirmation explicite :

```bash
sudo ./scripts/backup.sh /var/backups/digitalfootprint-avant-restauration.tar.gz
sudo ./scripts/restore.sh /var/backups/digitalfootprint-2026-10-14.tar.gz --yes
```

Le script vérifie le format, le moteur et la somme de contrôle avant restauration.
Il arrête temporairement le Web, le worker et la rétention s'ils étaient actifs,
puis rétablit leur état même en cas d'échec. Une archive SQLite ne peut pas être
restaurée dans PostgreSQL, ni l'inverse. Après restauration native, l'arborescence
d'état appartient au compte système et ne conserve aucun droit groupe ou autres.

Pour une installation native, `postgresql-client` et une version de
`pg_dump`/`pg_restore` compatible avec le serveur sont requis ; l'image runtime
Docker du backend inclut ce paquet. Le cycle PostgreSQL 17.11 `pg_dump` →
modification de donnée synthétique → `pg_restore` → vérification a été exécuté
localement sur un cluster temporaire sans port TCP. Testez aussi périodiquement les
restaurations sur une instance isolée de votre déploiement. Un test local ne prouve
pas que la sauvegarde est exploitable dans votre environnement.
