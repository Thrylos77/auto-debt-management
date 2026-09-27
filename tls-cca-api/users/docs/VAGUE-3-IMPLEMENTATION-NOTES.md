# Vague 3 — Configuration + Notifications

Cette vague introduit les deux services transverses prévus par l’architecture.

## Configuration

- `configuration.SystemSetting` remplace le `core.SystemSetting`.
- Les valeurs sont encodées en texte mais exposées avec leur type déclaré.
- Les clés autorisées sont déclarées dans `configuration.registry.definitions`.
- Les écritures sont centralisées dans `ConfigurationService` et auditées.
- Le paramètre CRM `customer_inactivity_duration_months` passe par cet API.
- Le script de démarrage migre les anciennes valeurs Core avant de retirer l’ancien modèle.

## Notifications

- Les notifications in-app sont persistées dans `Notification`.
- Les préférences utilisateur sont séparées du contenu des notifications.
- Les livraisons sont journalisées dans `NotificationDelivery`.
- Les templates personnalisables sont stockés dans `NotificationTemplate`.
- Les notifications de sécurité ne peuvent pas être désactivées par les préférences utilisateur.
- L’OTP de réinitialisation n’envoie plus de SMTP depuis `users` : il passe par `NotificationService` puis `EmailChannel`.

## URLs Users

`users.urls` est maintenant un package qui agrège :

- `users.urls.auth`
- `users.urls.account`
- `users.urls.security`

`config.v1_urls` ne référence que `users.urls` pour la surface Users. Les noms et chemins V1 existants sont conservés.


## Migration des anciens paramètres

La migration `configuration.0004_migrate_legacy_systemsetting` copie le paramètre
CRM historique avant que `core.0002_remove_systemsetting` ne supprime l'ancien modèle.
Le script `start_project.ps1` applique donc la chaîne de migrations plutôt que de
dépendre uniquement d'une commande manuelle de backfill.

## Legacy Users URLs

`users/legacy_urls.py` remains temporarily for backward compatibility with clients
using the pre-V1 `/api/users/` surface. Its URL names use a `legacy-` prefix so they
cannot shadow the canonical V1 URL names used by `users.urls`.

The canonical application structure remains:

- `users.urls.auth`
- `users.urls.account`
- `users.urls.security`

The legacy surface is planned for removal during the final hardening/deprecation step
after consumers have migrated to `/api/v1/`.
