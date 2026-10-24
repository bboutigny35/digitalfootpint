# Surveillance de l'exposition des données sensibles

## Analyse d'impact

Le module réutilise l'authentification par session, CSRF, `owner_id`, les événements
d'audit et SQLAlchemy/Alembic. Il possède son propre contrat fournisseur afin
d'empêcher qu'un NIR, un PAN ou un numéro de pièce ne soit accidentellement envoyé
à un connecteur OSINT généraliste.

Les valeurs brutes ne sont jamais persistées. NIR et pièce d'identité sont validés
de façon éphémère. Une carte est représentée uniquement par le réseau déclaré et
les quatre derniers chiffres. Téléphone, adresse et IBAN deviennent un libellé
masqué et une empreinte HMAC-SHA-256 avec séparation de domaine. Cette empreinte
n'est ni un hash simple ni un moyen de retrouver la valeur ; elle sert seulement à
une comparaison locale exacte avec une source autorisée préparée de la même façon.

```text
requête authentifiée
  -> validation locale en mémoire
  -> masque + HMAC (si conservation autorisée)
  -> descripteur appartenant à l'utilisateur
  -> contrôle local par adaptateur autorisé
  -> constatation sans valeur brute -> alerte sans valeur brute
```

## Tables

- `sensitive_descriptors` : catégorie, masque, empreinte et expiration facultative ;
- `sensitive_consents` : fournisseur, catégorie, confirmation et révocation ;
- `sensitive_checks` : historique, statut, source et indicateur de transmission ;
- `sensitive_findings` : correspondance, risque, statut et recommandation ;
- `sensitive_alerts` : notification interne sans identifiant sensible.

Les listes de constatations et d'alertes appliquent systématiquement `owner_id`.
Une alerte peut être marquée comme prise en compte ; cette action est protégée par
CSRF et produit un événement d'audit limité à la catégorie et au niveau de risque.
Elle ne supprime ni la constatation ni l'historique du contrôle.

## Limites

La présence d'une empreinte dans une source autorisée prouve seulement une égalité
technique avec cette source. L'absence d'alerte ne démontre jamais l'absence de
compromission. Aucun fournisseur externe n'est activé dans l'incrément initial et
aucune recherche dans des bases volées n'est prévue.
