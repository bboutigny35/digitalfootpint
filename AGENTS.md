# Instructions aux contributeurs automatisés

- Lire `docs/development/progress.md` avant toute modification importante.
- Ne jamais journaliser mots de passe, jetons, clés API, e-mails complets ou données d'identité.
- Les accès réseau de tests sont interdits par défaut. Utiliser des transports HTTP simulés.
- Toute URL distante non fiable doit passer par le validateur SSRF, y compris à chaque redirection.
- Préserver la compatibilité SQLite et PostgreSQL et fournir une migration Alembic.
- Mettre à jour les tests et la documentation avec chaque comportement public.
- Ne pas déclarer une phase terminée si ses critères ne sont pas tous vérifiés.
