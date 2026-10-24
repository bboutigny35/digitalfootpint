# Conservation des données sensibles

## Politique par catégorie

| Catégorie | Valeur brute | Donnée conservée | Transmission généraliste |
|---|---|---|---|
| NIR | Éphémère uniquement | Aucune | Interdite |
| Carte bancaire | Refusée par l'API | Réseau et quatre derniers chiffres | Interdite |
| IBAN | Éphémère à l'enregistrement | Masque et HMAC lié à l'installation | Interdite par défaut |
| Téléphone | Éphémère à l'enregistrement | Masque et HMAC lié à l'installation | Confirmation requise |
| Adresse | Éphémère à l'enregistrement | Libellé générique et HMAC | Confirmation requise |
| Pièce d'identité | Éphémère uniquement | Aucune | Interdite |

Une expiration facultative de 1 à 365 jours peut être appliquée aux descripteurs.
La suppression retire masque, empreinte et métadonnées ; l'historique de contrôle
conserve seulement catégorie, fournisseur et statut avec une référence devenue
nulle. Les sauvegardes peuvent conserver une ancienne copie jusqu'à expiration de
leur propre cycle et doivent donc être chiffrées et purgées conformément à celui-ci.

La commande suivante traite au maximum 500 descripteurs expirés par invocation :

```bash
cd /opt/digitalfootprint/backend
sudo -u digitalfootprint .venv/bin/digitalfootprint-retention
```

Sa sortie JSON contient uniquement le nombre de suppressions et l'heure du seuil.
Elle ne contient ni masque, ni empreinte, ni identifiant utilisateur. L'installation
native utilise `digitalfootprint-retention.timer`, quotidien avec un délai aléatoire
maximal de 30 minutes. En cas de volume supérieur à 500, les éléments restants sont
traités lors de l'exécution suivante ; la commande peut être relancée sans danger.

Contrôler le timer et la dernière exécution :

```bash
systemctl status digitalfootprint-retention.timer
journalctl -u digitalfootprint-retention.service --since today
```

La clé d'installation protège les empreintes HMAC. Sa rotation invalide les
comparaisons existantes : les descripteurs doivent alors être supprimés et recréés.
