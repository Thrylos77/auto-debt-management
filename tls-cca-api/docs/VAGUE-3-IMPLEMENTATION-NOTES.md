# Vague 3 — Configuration + Notifications

Cette vague a introduit les deux services transverses prévus par l'architecture.
Les éléments de migration legacy ci-dessous décrivent uniquement l'historique
de transition ; ils ne font plus partie des commandes opérationnelles courantes.

## Configuration

- `configuration.SystemSetting` remplace le `core.SystemSetting`.
- Les valeurs sont encodées en texte mais exposées avec leur type déclaré.
- Les clés autorisées sont déclarées dans `configuration.registry.definitions`.
- Les écritures sont centralisées dans `ConfigurationService` et auditées.
- Le paramètre CRM `customer_inactivity_duration_months` passe par cet API.

## Notifications

- Les notifications in-app sont persistées dans `Notification`.
- Les préférences utilisateur sont séparées du contenu des notifications.
- Les livraisons sont journalisées dans `NotificationDelivery`.
- Les templates personnalisables sont stockés dans `NotificationTemplate`.
- Les notifications de sécurité ne peuvent pas être désactivées par les préférences utilisateur.
- L'OTP de réinitialisation passe par `NotificationService` puis `EmailChannel`.

## URLs Users

`users.urls` est maintenant un package qui agrège :

- `users.urls.auth`
- `users.urls.account`
- `users.urls.security`

`config.v1_urls` ne référence que `users.urls` pour la surface Users. Les noms et chemins V1 sont conservés.

## Migrations historiques

La migration `configuration.0004_migrate_legacy_systemsetting` reste conservée dans
l'historique Django afin de préserver la chaîne de migration des bases existantes.
Elle ne doit pas être remplacée par une commande manuelle de backfill lors des
déploiements actuels.

Les anciens modules de routes Users et les commandes de migration ponctuelle ont
été retirés lors de la finalisation de la Vague 4.
