# DigitalFootprint

DigitalFootprint est une plateforme Web auto-hébergée de recherche et de suivi
de son empreinte numérique publique. Le projet privilégie le consentement, la
minimisation des données et des connecteurs utilisant des API officielles.

> État : version de développement. Le socle authentifié, le worker persistant,
> les connecteurs GitHub, GitLab, Bluesky, Wayback, Brave Search facultatif et SearXNG local,
> l'interface principale, la planification, la comparaison des scans, les notifications
> internes, les exports et le suivi des demandes RGPD sont implémentés et testés.
> Brave n'envoie que noms et pseudonymes, après confirmation, et peut entraîner
> des frais selon le compte fournisseur. Des vérifications de déploiement et
> d'audit restent ouvertes.
> Voir [l'avancement](docs/development/progress.md).

Le worker persistant sait également traiter la file de crawl Web : respect de
`robots.txt`, quota par domaine, validation SSRF de chaque redirection et limites
strictes de type et de taille. Seul le texte minimisé est conservé, jamais le
corps HTML brut. Les sources sitemap/feed doivent être activées par un
administrateur ; seuls les connecteurs déclarant explicitement leurs résultats
explorables alimentent cette file, après une nouvelle validation de chaque URL.
Cette chaîne reste une fonctionnalité de développement et ne garantit ni
l'exhaustivité ni l'attribution d'une page à une identité.

L’écran Recherches propose une **Recherche globale** : il lance les connecteurs
activés, prêts et compatibles avec le profil en une action. Le périmètre reste
celui des fournisseurs configurés et de leurs index. SearXNG local peut agréger
plusieurs moteurs sans clé fournisseur par utilisateur, mais les moteurs amont
peuvent limiter ou bloquer les requêtes. Après confirmation, seuls noms et
pseudonymes sont transmis à ces moteurs. GitHub, GitLab, Bluesky et Wayback apportent des
sources spécialisées. Aucun résultat ne garantit une couverture exhaustive du Web.

Le backend comprend désormais un premier module cloisonné de surveillance des
données sensibles. Il ne conserve aucune valeur brute, refuse PAN/CVV/PIN et
n'active aucun fournisseur externe. Voir
[`docs/architecture/sensitive-monitor.md`](docs/architecture/sensitive-monitor.md).

Le registre des demandes de suppression prépare des modèles de courrier et suit
les réponses sans jamais contacter automatiquement un organisme. Voir le
[guide des demandes RGPD](docs/user-guide/removal-requests.md).

La navigation, l’écran de connexion et les principales pages métier peuvent être
affichés en français ou en anglais (préférence locale au navigateur). Les contenus
fournis par les sources et certains messages externes restent dans leur langue
d’origine.

## Développement du backend

Prérequis : Python 3.11 à 3.13 et `pip`.

```bash
cd backend
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
cp ../.env.example ../.env
alembic upgrade head
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Documentation OpenAPI : `http://127.0.0.1:8000/docs`. La première inscription
crée l'administrateur local ; les inscriptions suivantes sont refusées.

```bash
cd backend
pytest
ruff check .
mypy app
```

La documentation d'architecture et les limites connues se trouvent dans
[`docs/`](docs/).

Pour la chaîne de découverte Web, consulter l'[audit](docs/WEB_DISCOVERY_AUDIT.md),
l'[architecture](docs/WEB_DISCOVERY_ARCHITECTURE.md), la
[configuration](docs/WEB_DISCOVERY_CONFIGURATION.md), la
[sécurité](docs/WEB_DISCOVERY_SECURITY.md), l'[API](docs/WEB_DISCOVERY_API.md), le
[déploiement](docs/WEB_DISCOVERY_DEPLOYMENT.md) et les
[tests](docs/WEB_DISCOVERY_TESTS.md). La corrélation est décrite dans
[`docs/IDENTITY_CORRELATION.md`](docs/IDENTITY_CORRELATION.md), la préparation
d'une version dans [`docs/RELEASE_PROCESS.md`](docs/RELEASE_PROCESS.md) et son
[état de préparation](docs/RELEASE_READINESS.md).
La [revue contractuelle des fournisseurs](docs/PROVIDER_LEGAL_REVIEW.md) recense
les blocages à lever avant toute activation externe réelle.

## Démarrage Docker Compose

Après avoir remplacé la clé d'exemple dans `.env` :

```bash
docker compose build
docker compose up -d --wait
```

Ouvrez `http://127.0.0.1:8080`. SQLite est utilisé par défaut dans un volume
persistant ; la variante PostgreSQL et les procédures de sauvegarde sont décrites
dans [l'installation Docker](docs/installation/docker.md).

Pour activer SearXNG, générez un secret aléatoire, définissez `SEARXNG_SECRET` dans
`.env`, puis démarrez aussi l'overlay `compose.searxng.yaml` (détails dans le guide
Docker). Sans cet overlay, le connecteur reste non configuré.

## Générer les guides PDF

Après installation de l'environnement backend :

```bash
./scripts/generate-docs-pdf.sh
```

Les guides utilisateur et administrateur sont produits dans
`reports/documentation/` directement depuis les fichiers Markdown de `docs/`.
