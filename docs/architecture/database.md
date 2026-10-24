# Modèle de données initial

- `users` : compte local, rôle administrateur, condensat Argon2id.
- `auth_sessions` : jetons et CSRF hachés, expiration et propriétaire.
- `identity_profiles` : identité, variantes, pseudonymes, contacts et contexte.
- `scans` : profil, connecteurs demandés, état, progression et horodatages.
- `scan_schedules` : fréquence et prochaine échéance des scans persistants.
- `results` : URL canonique, provenance, extrait, statut et score expliqué.
- `report_exports` : historique minimisé des rapports générés, sans fichier conservé.
- `removal_requests` : organisme, mention facultative, statut, dates et notes de suivi.
- `notification_preferences` : activation des alertes de nouvelles mentions.
- `notifications` : alertes internes minimisées, scan associé et date de lecture.
- `audit_events` : action, acteur et ressource, sans secret ni donnée brute.

La contrainte `(scan_id, canonical_url)` déduplique un résultat dans un scan. Une
future empreinte normalisée permettra la comparaison entre scans. Toutes les
ressources métier portent un `owner_id`; les requêtes API doivent toujours
l'inclure. Les suppressions de compte/profil sont en cascade, tandis que l'acteur
d'un événement d'audit devient nul.

La suppression d'une mention conserve son dossier de suppression en mettant
`result_id` à `NULL`. La suppression d'un utilisateur efface ses dossiers en
cascade. Alembic est l'unique mécanisme de modification du schéma en production.
