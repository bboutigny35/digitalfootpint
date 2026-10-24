# Rapports

Ouvrez **Rapports**, choisissez une synthèse ou un rapport détaillé, puis le format :

- CSV ou XLSX pour un traitement tabulaire ;
- JSON pour un traitement automatisé ;
- HTML pour une consultation locale ;
- PDF pour un document figé.

La synthèse contient le périmètre, la date de génération, les sources interrogées
ou indisponibles, le nombre de résultats et les limites méthodologiques. Le rapport
détaillé ajoute les URL, extraits, niveaux de confiance, statuts et dates.

Les exports ne contiennent pas les descripteurs du module de données sensibles.
Les cellules pouvant être interprétées comme des formules sont neutralisées dans
CSV/XLSX. Le HTML échappe les contenus distants et interdit les ressources réseau
avec une CSP. Le PDF est généré localement sans charger de ressource distante.

Les fichiers contiennent néanmoins des données personnelles publiques. Stockez-les
sur un support chiffré, limitez leur conservation et contrôlez leurs destinataires.
L'historique conserve le format, le type, le périmètre, la date et le nombre de
résultats, en plus du journal d'audit. Les fichiers eux-mêmes ne sont jamais
conservés par le serveur.
