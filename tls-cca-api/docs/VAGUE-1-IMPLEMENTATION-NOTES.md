# Vague 1 — Notes d'implémentation

La Vague 1 a introduit les frontières cibles de l'architecture. Les éléments
de compatibilité décrits ci-dessous sont des notes historiques : ils ont été
supprimés pendant la finalisation de la Vague 4 lorsque la migration vers les
contrats canoniques a été considérée comme terminée.

## Baseline migrations

L'archive de la Vague 1 ne contenait aucune migration Django. Les changements
de modèles devaient être accompagnés de migrations générées dans l'environnement
Poetry du projet avant déploiement sur une base vierge.

## Corrections de validation Django

- `CustomUserAdmin` n'ordonne plus deux fois le champ `groups` dans ses `fieldsets`.
- Les index de `TwoFASetup` et `TwoFAChallenge` utilisent des noms <= 30 caractères
  pour respecter la limite Django.
- Des tests dédiés couvrent ces régressions.
