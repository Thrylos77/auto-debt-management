# Final Hardening — rollback et exploitation

## 1. Avant déploiement

Effectuer une sauvegarde de la base de données et conserver le dernier artefact applicatif stable de la vague 4. Vérifier `makemigrations --check --dry-run` et appliquer les migrations dans un environnement de préproduction avant production.

## 2. Suppression des routes legacy

La suppression des routes ne modifie pas les données. Un rollback applicatif consiste à redéployer l'artefact précédent et sa configuration de routage. Aucun rollback de migration n'est requis pour cette partie.

## 3. Suppression des champs User legacy

La migration générée localement par Django supprimera les anciens champs `roles`, `groups`, `totp_secret` et `is_2fa_enabled`. Vérifier avant migration que le backfill RBAC et la migration 2FA ont déjà été exécutés. Conserver une sauvegarde de la base avant application. Pour un retour arrière après migration, restaurer la base sauvegardée et redéployer l'artefact précédent ; ne pas tenter de recréer ces colonnes manuellement.

## 4. Rotation de la clé JWT

`JWT_SIGNING_KEY` est désormais distincte de `DJANGO_SECRET_KEY` en production. Changer cette valeur invalide immédiatement les JWT signés avec l'ancienne clé. Le rollback consiste à restaurer l'ancienne clé, uniquement pendant la fenêtre d'intervention définie.

## 5. CORS, limites et headers

Les paramètres CORS, `API_MAX_REQUEST_BYTES`, `DATA_UPLOAD_MAX_NUMBER_FIELDS`, `DATA_UPLOAD_MAX_NUMBER_FILES` et `FILE_UPLOAD_MAX_MEMORY_SIZE` sont pilotés par environnement. En cas de régression, revenir aux valeurs précédentes dans la configuration de déploiement puis redémarrer l'application.

## 6. Exercice de rollback à reproduire en préproduction

1. Déployer la version durcie.
2. Vérifier les endpoints `/api/v1/`, le schéma OpenAPI et l'authentification.
3. Modifier temporairement `JWT_SIGNING_KEY` et constater que les anciens tokens sont refusés.
4. Restaurer la clé précédente et vérifier le comportement attendu des tokens encore valides.
5. Restaurer l'artefact précédent et confirmer que les données métier restent intactes.

L'exercice doit être consigné dans le journal de déploiement avec la date, le responsable et le résultat.
