# Recherches et surveillance

Créez d'abord un profil dans **Identités**, avec au moins un pseudonyme, puis ouvrez
**Recherches** et sélectionnez ce profil. Le bouton **Recherche globale** lance
automatiquement les connecteurs activés, prêts et compatibles avec les champs du
profil. Le fournisseur de recherche Web généraliste doit être configuré pour que
ce bouton soit disponible ; les connecteurs spécialisés seuls ne sont pas présentés
comme une recherche générale du Web. Les requêtes restent bornées par les quotas
locaux et ceux des fournisseurs, et ne couvrent que les pages indexées par ces
services.

GitHub consulte les profils publics
exacts via son API officielle. GitLab vérifie le point de statut public officiel
pour chaque pseudonyme ; il ne transmet ni nom ni adresse électronique. Wayback
vérifie les captures des domaines et sites connus du profil, sans transmettre les
pseudonymes, noms ou e-mails. Ces correspondances de pseudonyme ne prouvent jamais
l'identité du titulaire. Le scan
continue dans le worker même si le navigateur est fermé et peut être annulé depuis
l'historique.

SearXNG est l'option conseillée pour la recherche généraliste sans clé d'API
externe individuelle. L'administrateur doit toutefois installer et activer une
instance locale. Si vous sélectionnez SearXNG, l'application demande confirmation :
seuls le nom complet et les pseudonymes sont transmis à l'instance locale, qui les
relaie aux moteurs activés. Les pratiques de conservation et limites diffèrent
selon ces moteurs ; une requête peut être refusée ou ne donner aucun résultat.
Les e-mails, domaines, variantes orthographiques et mots-clés ne sont pas envoyés.

Brave Search est un connecteur facultatif. Si vous le sélectionnez, l'application
affiche les données transmises et demande votre confirmation avant le scan : seuls
les noms complets et pseudonymes sont envoyés à l'API Brave ;
les e-mails et mots-clés ne le sont pas. Cette utilisation peut entraîner des
frais selon votre compte. La notice Brave actuellement publiée indique que des
journaux de requêtes peuvent être conservés jusqu'à 90 jours ; vérifiez les
conditions en vigueur avant activation. L'absence de résultat ne prouve pas
l'absence de mention.

Les libellés, filtres, statuts et comparaisons de l’espace de travail suivent la
langue de l’interface. Les titres, extraits et notes de méthode provenant des
sources ou du service restent dans leur langue d’origine.

Les résultats apparaissent dans **Résultats**. Classez chaque mention comme
confirmée, probable, incertaine, faux positif ou ignorée. Un résultat « probable »
ou un score élevé reste un indice à vérifier, jamais une preuve d'identité.

La liste est paginée côté serveur. Elle peut être filtrée par texte, source,
domaine exact et statut de validation, puis triée par date, score, titre ou
domaine. Les filtres ne modifient ni ne suppriment les résultats conservés.

## Surveillance planifiée

Dans **Surveillance**, choisissez un profil puis une fréquence quotidienne,
hebdomadaire ou mensuelle. La première exécution est mise en file par le worker,
puis l'échéance suivante est calculée et conservée en base. Une période d'arrêt ne
crée pas une rafale de scans rétroactifs : une seule exécution est créée et la
prochaine échéance est avancée dans le futur.

Les libellés et contrôles de cette page suivent la langue de l’interface. Les
titres et textes des notifications sont conservés tels qu’ils ont été générés ;
ils ne sont pas traduits à l’affichage.

Une planification peut être mise en pause, réactivée ou supprimée. Ces opérations
n'effacent ni les scans déjà exécutés ni leurs résultats.

## Notifications internes

La page **Surveillance** permet d’activer ou désactiver les alertes de nouvelles
mentions. Après un scan, DigitalFootprint compare ses résultats au précédent scan
terminé du même profil. Une alerte locale est créée si de nouvelles URL sont
présentes. Le premier scan ne génère donc pas d’alerte comparative.

Les alertes sont consultables et peuvent être marquées comme lues. Elles restent
dans l’application : aucun e-mail, SMS ou webhook n’est envoyé.

## Comparer deux recherches

La page **Recherches** permet de sélectionner deux scans terminés portant sur
le même profil. DigitalFootprint classe les URL dans six catégories : nouvelles,
déjà connues, modifiées, inaccessibles confirmées, non revérifiées et faux
positifs exclus.

Une URL présente dans le scan de référence mais absente du scan récent est
classée **non revérifiée**. Cette absence ne constitue pas une preuve de
suppression ou d'inaccessibilité. La catégorie « inaccessible » reste vide tant
qu'un contrôle explicite et sûr de disponibilité n'a pas établi cet état.
