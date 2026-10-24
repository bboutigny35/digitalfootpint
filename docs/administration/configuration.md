# Configuration

Copier `.env.example` vers `.env`. Les variables utilisent le préfixe
`DIGITALFOOTPRINT_`. En production, générer une clé aléatoire d'au moins 32 caractères,
activer `COOKIE_SECURE`, restreindre hôtes/origines et ne jamais versionner `.env`.

La page **Administration**, réservée aux administrateurs, permet d'enregistrer ou
de supprimer les clés GitHub et Brave Search mais n’en affiche jamais les valeurs. Elle présente
également le type de base de données, le mode du cookie, l’état des connecteurs et
le journal d’audit filtré. Les mutations exigent une session administrateur et un
jeton CSRF.

Les libellés de la page d’administration suivent la langue de l’interface. Les
identifiants de connecteurs, états techniques, actions d’audit et commandes restent
affichés tels qu’ils sont fournis par le système.

## Coffre des connecteurs

Les secrets administrables sont chiffrés par AES-256-GCM. La clé maître ne doit
jamais être placée en base : elle reste dans le fichier d'environnement protégé.
Générer une première clé :

```bash
python3 -c 'import base64,secrets; print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())'
```

Configurer ensuite, sans guillemets et sans espace :

```dotenv
DIGITALFOOTPRINT_CONNECTOR_SECRET_KEYS=v1:VALEUR_BASE64_GENEREE
DIGITALFOOTPRINT_CONNECTOR_SECRET_ACTIVE_KEY=v1
```

Pour effectuer une rotation, générer une seconde clé, conserver temporairement
les deux versions et désigner la nouvelle comme active :

```dotenv
DIGITALFOOTPRINT_CONNECTOR_SECRET_KEYS=v1:ANCIENNE_VALEUR,v2:NOUVELLE_VALEUR
DIGITALFOOTPRINT_CONNECTOR_SECRET_ACTIVE_KEY=v2
```

Redémarrer le service Web, cliquer sur **Appliquer la rotation**, vérifier que les
secrets indiquent `v2`. Le worker recharge les secrets avant le prochain scan.
L'ancienne clé peut seulement
être retirée après cette vérification et une sauvegarde testée. Une clé perdue ne
peut pas être récupérée depuis la base.

La variable historique `DIGITALFOOTPRINT_GITHUB_API_TOKEN` reste acceptée comme
solution de repli quand aucun secret GitHub n'est enregistré en base.

Brave Search est facultatif et non prêt par absence de clé : aucune recherche ni
résultat simulé n'est produit sans configuration. Enregistrer la clé Brave dans
le coffre administrable ou définir `DIGITALFOOTPRINT_BRAVE_API_TOKEN`. Lorsqu'un
scan sélectionne Brave, les requêtes incluent le nom complet et les pseudonymes du
profil ; les e-mails, variantes de nom et mots-clés ne sont pas transmis. Chaque
requête passe par l'API externe, qui voit le terme recherché. Son plan peut
facturer l'usage et les conditions de conservation dépendent du contrat du
fournisseur ; la notice Brave indique une conservation possible des journaux de
requêtes jusqu'à 90 jours. Consulter ses
[tarifs](https://api-dashboard.search.brave.com/documentation/pricing) et conditions
avant activation. La limite locale est de cinq requêtes par minute et le nombre
de requêtes par scan est borné.

### SearXNG local

En mode Debian natif, si Docker Compose est installé, l'installateur génère une
clé `SEARXNG_SECRET` indépendante et configure l'endpoint local. Elle est conservée
dans `/etc/digitalfootprint/searxng.env`, possédé par root et mode `0600`. En
Compose, fournir un secret aléatoire dans `SEARXNG_SECRET` puis activer
`compose.searxng.yaml`. Le connecteur n'accepte que les deux endpoints définis
pour ces modes d'installation ; il est « non prêt » si l'instance locale n'est
pas configurée.

SearXNG relaie les requêtes aux moteurs activés sur l'instance. À chaque scan,
l'interface et l'API exigent une confirmation explicite ; uniquement noms et
pseudonymes sont envoyés. Les e-mails, domaines et mots-clés sont exclus. Les
requêtes partent en POST et ne sont pas placées dans l'URL DigitalFootprint.
Cette précaution n'empêche pas les moteurs amont de journaliser les termes ou de
leur appliquer leurs propres politiques et quotas.

## Activation des connecteurs

Un administrateur peut activer ou désactiver chaque connecteur depuis la même
page. La désactivation refuse immédiatement les nouveaux scans et nouvelles
planifications, suspend les planifications existantes concernées et annule les
scans encore en attente ou en cours. Elle ne supprime aucun résultat historique.

Le worker recharge les connecteurs et leurs secrets avant chaque scan : une clé
enregistrée dans le coffre est utilisable à la prochaine recherche sans redémarrage.
L'interface exige une confirmation avant une désactivation et l'action est inscrite
dans le journal d'audit.

## Sauvegarde depuis l'administration

Le bouton **Télécharger une sauvegarde** crée une archive à partir de la base
configurée, sans accepter de chemin ni de commande provenant du navigateur. Une
seule création peut s'exécuter à la fois. L'archive temporaire est supprimée dès
la fin du transfert et la réponse porte `Cache-Control: no-store`.

Cette opération exige une confirmation, une session administrateur et le jeton
CSRF. Elle est auditée. La restauration reste volontairement limitée aux scripts
locaux avec confirmation explicite, car elle remplace les données existantes.
