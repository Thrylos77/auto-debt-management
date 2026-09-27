# Vague 1 — Notes d'implémentation

La Vague 1 introduit les frontières cibles sans suppression destructive des données historiques.

## Compatibilité temporaire

- `User.roles`, `User.groups`, `User.totp_secret` et `User.is_2fa_enabled` restent présents.
- `users/services/user_services.py`, `otp_services.py` et `twofa_services.py` sont des wrappers de compatibilité.
- `/api/users/` et les routes `/api/token/...` restent des alias vers les mêmes services.
- Le transfert de portefeuille est désormais déclenché par le signal `users.events.user_deactivated`; `users` n'importe plus `crm`.

## Baseline migrations

L'archive initiale ne contenait aucune migration Django. Les changements de modèles de cette Vague 1 doivent être accompagnés de migrations initiales générées par `makemigrations` dans l'environnement Poetry du projet avant déploiement sur une base vierge. L'environnement d'analyse utilisé ici ne dispose pas des dépendances Django installées et n'a pas accès à l'index Python ; il est donc volontairement exclu de générer des migrations manuelles non vérifiées.


## Corrections de validation Django

- `CustomUserAdmin` n'ordonne plus deux fois le champ `groups` dans ses `fieldsets`; le champ `groups` reste géré par `UserAdmin` pendant la période de compatibilité.
- Les index de `TwoFASetup` et `TwoFAChallenge` utilisent des noms <= 30 caractères pour respecter la limite Django.
- Tests dédiés ajoutés dans `users/tests/test_v1_identity.py` pour empêcher la réintroduction de ces deux problèmes.
