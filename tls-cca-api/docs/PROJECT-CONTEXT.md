# PROJECT-CONTEXT

> Document de **contexte** du projet (≠ README). Il reprend et complète certaines
> sections du README, et sert de référence de compréhension globale : objectif,
> acteurs, rôles, fonctionnalités, contraintes métier et technologies.
> Complété à partir du code (`models`, `serializers`, `services`, `views`, `urls`)
> et des fichiers de référence dans `docs/`.

---

## Nom du projet

**TLS CCA — Auto Debt Management** (nom du package backend : `tls-cca-api`)

- API backend : **TLS CCA API**
- Référentiel : `https://github.com/Thrylos77/auto-debt-management`
- Branche par défaut : `main`

---

## Objectif

Mettre à disposition une plateforme web complète de **gestion de la dette / du
recouvrement dans le secteur de la concession automobile (CCA)**. Le système
permet de gérer intégralement le cycle de vie d'un dossier de crédit :

- la **relation client** (CRM : clients et portefeuilles),
- la **vente à crédit** (crédit-sales),
- les **créances et échéances** (debts & terms),
- le **recouvrement** (recoveries / paiements),
- le **reporting / tableau de bord** (KPIs, aging, evolution),
- la **sécurité et le contrôle d'accès** (utilisateurs, rôles, permissions).

---

## Utilisateurs

Le contexte métier (« concession auto ») distingue principalement :

- **Administrateur** — pilote l'ensemble du système (utilisateurs, rôles, données).
- **Gestionnaire / Consultant** — gestion des utilisateurs, suivi global et reporting.
- **Agent / Commercial** — saisie des clients, des ventes, et du recouvrement sur le terrain.

> Certains de ces acteurs peuvent correspondre au rôle technique **COMMERCIAL**
> (voir section Rôles ci-dessous). La liste n'est pas exhaustive et reste à
> affiner selon le frontend et les cas d'usage réels.

---

## Rôles

Le RBAC est modulaire (`rbac` app) : un **rôle** (`Role`) regroupe des
**permissions** (`Permission`, format `resource.action`) ; un **groupe** (`Group`)
regroupe des rôles. La configuration de référence est dans
`rbac/fixtures/permissions_config.json` (seed via `python manage.py seed_rbac_v2`).

Rôles définis :

- **ADMIN** — bénéficie de *toutes* les permissions (`permissions: ALL`).
  Usage exclusivement administratif.
- **COMMERCIAL** — rôle **par défaut** d'un nouvel utilisateur. Gère son propre
  profil et ses clients (vision restreinte à ses portefeuilles normalement).
- **CONSULTANT / Gestionnaire** — peut créer/gérer des utilisateurs, lister tous
  les clients (`customer.list_all`) et consulter le reporting.
- **MODIFICATEUR** — peut consulter et modifier son propre profil, et lister
  tous les clients (lecture).

> **Attention aux écarts de nommage souhaité :** la maquette métier évoque
> « Administrateur », « Gestionnaire » et « Agent », alors que les rôles
> techniques actuellement seedés sont `ADMIN`, `CONSULTANT`, `COMMERCIAL`,
> `MODIFICATEUR`. À harmoniser entre le frontend et le backend si nécessaire.

Permissions couvertes (extrait) : `user.*`, `user_history.*`, `permission.*`,
`role.*`, `group.*`, `rbac.assign_role/remove_role/...`, `customer.*`,
`customer_history.*`, `portfolio.*`, `credit_sale.*`, `debt.*`, `term.*`,
`recovery.*`, `reporting_dashboard.view`, `reporting_aging.view`,
`reporting_evolution.view`.

---

## Fonctionnalités

### Utilisateurs & Authentification (`users` app)

- Inscription (`/api/users/register/`), connexion JWT (`/api/token/login/`),
  rafraîchissement (`refresh`), vérification (`verify`), déconnexion avec
  blacklist du refresh token (`/api/token/logout/`).
- Profil (`/api/users/me/`), gestion des utilisateurs (`/api/users/`),
  réactivation (`/api/users/{id}/reactivate/`).
- **Soft delete** : la suppression d'un utilisateur le **désactive**
  (`is_active=False`) plutôt que de le détruire — l'historique est conservé.
- Réinitialisation de mot de passe par **OTP** (e-mail) et gestion des mots de
  passe (propre / par un admin).
- **2FA / TOTP** (Google Authenticator) : activation, désactivation, login 2 étapes.
- Historique complet des utilisateurs (`/api/users/history/`) via `django-simple-history`.

### RBAC (`rbac` app)

- Permissions, rôles et groupes ; assignation de rôles aux utilisateurs, de rôles
  aux groupes ; historique (audit) des permissions/rôles/groupes.
- Contrôle d'accès automatique par permission (`AutoPermissionMixin`).

### CRM (`crm` app)

- **Clients** : personnes physiques et morales, gestion des détails imbriqués,
  activation/désactivation, **désactivation automatique** des clients sans
  activité depuis une durée configurable (par défaut **48 mois / 4 ans**).
- **Portefeuilles (`Portfolio`)** : création, attribution et **transfert**.
  Chaque portefeuille appartient à un commercial et possède une référence unique
  (`PF-XXX`), un solde (`balance`) et un statut `active`.

#### Assignation / transfert de portefeuille *(fonctionnalité métier)*

- **Attribution d'un portefeuille existant** : `POST /api/portfolios/{id}/assign/`
  avec `{ "commercial": <id>, "reason": "..." }`.
- **Transfert du portefeuille d'un commercial sortant** :
  `POST /api/portfolios/{id}/transfer/` avec `{ "to_commercial": <id>, "reason": "..." }`,
  ainsi qu'un transfert de masse (tous les portefeuilles **actifs** d'un commercial)
  déclenché à la désactivation d'un utilisateur (`soft_delete_user(..., transfer_to=...)`).
- **Journalisation** : chaque assignation/transfert est tracé dans
  `PortfolioTransfer` (`from_commercial`, `to_commercial`, `transferred_by`,
  `reason`, `transferred_at`) — consultable via `/api/portfolio-transfers/`.
- Règles métier : le commercial cible **doit être actif**, refus de ré-assigner au
  même possesseur, le portefeuille est **réactivé** à l'assignation, opérations
  **atomiques**.

### Ventes (`sales` app)

- **Ventes à crédit (`CreditSale`)** : client, commercial, portefeuille (par défaut
  le premier portefeuille actif du commercial), montant total, acompte (`deposit`),
  statut (`pending_approval`, `approved`, `rejected`, `cancelled`), justificatif PDF.

### Créances & Recouvrement (`receivables` app)

- **Dettes (`Debt`)** : créance liée à une vente, montant initial, solde restant,
  mensualité, durée, statut (`not_started`, `ongoing`, `overdue`, `paid`).
- **Échéances (`Term`)** : échéancier lié à une dette avec statuts
  (`unpaid`, `partially_paid`, `paid`, `overdue`, `partially_overdue`).
- **Recouvrements (`Recovery`)** : paiements sur une échéance avec mode de paiement
  (`cash`, `credit_card`, `bank_transfer`, `check`, `other`) et reçu.
- Mise à jour automatique des statuts de dettes/échéances selon les dates et soldes.

### Reporting (`reporting` app)

- Tableau de bord global (KPIs), **Aging** (balance par ancienneté) et **évolution**
  du recouvrement. Statistiques et recherches génériques dans `core`.

### Documentation API

- Swagger UI : `/api/docs/` | Redoc : `/api/schema/redoc/`
- Schéma OpenAPI : `/api/schema/` (via `drf-spectacular`).

---

## Contraintes métier

- **Soft delete** des utilisateurs : jamais de suppression physique ; les
  portefeuilles d'un « commercial sortant » doivent pouvoir être **transférés**
  avant désactivation.
- **Désactivation automatique** des clients : la durée d'inactivité (en **mois**)
  est **configurable par l'Administrateur** (`GET/PATCH
  /api/crm/customers/deactivation-policy/`), par défaut **48 mois (4 ans)** ; un
  client est désactivé si sa dernière activité (vente, dette close ou création)
  est antérieure à ce seuil.
- **Portefeuilles** : référence unique `PF-XXX` ; `on_delete=PROTECT` sur le
  commercial ; solde ≥ 0 ; transfert journalisé ; le commercial cible doit être
  actif.
- **Dettes** : le **solde restant ne peut pas dépasser le montant initial**
  (`Debt.clean()`), montants ≥ 0 (validators `MinValueValidator`).
- **Portefeuille par défaut** : une vente sans portefeuille utilise le premier
  portefeuille **actif** du commercial.
- **Intégrité référentielle forte** : la plupart des FK utilisent
  `on_delete=PROTECT` (clients, ventes) pour préserver l'historique.
- **Traçabilité / audit** : tous les modèles clés sont versionnés avec
  `django-simple-history` (historique consultable via API et admin).

---

## Technologies

- **Backend :** Django 5.2 + Django REST Framework
- **Frontend :** React JS *(prévu / connecté à cette API)*
- **Database :** PostgreSQL (`psycopg` / `psycopg-binary`)
- **Auth :** JWT (`djangorestframework-simplejwt`, blacklist des refresh tokens)
  + **2FA/TOTP** (`pyotp`, `qrcode[pil]`)
- **Documentation API :** `drf-spectacular` (+ `drf-spectacular-sidecar`)
- **Filtrage :** `django-filter`
- **Audit / Historique :** `django-simple-history`
- **RBAC :** système maison (`rbac` app) avec `Permission` / `Role` / `Group`
- **Gestion de dépendances :** Poetry (`pyproject.toml`), Python 3.12+
- **Tests :** `pytest`, `pytest-django`, `pytest-cov`, `faker`, `factory-boy`
- **Qualité :** `black`

### Django Apps

| App             | Rôle                                                        |
| --------------- | ------------------------------------------------------------ |
| `users`       | Utilisateurs, auth JWT, OTP, 2FA, historique                 |
| `rbac`        | Permissions, rôles, groupes, contrôle d'accès             |
| `core`        | Utilitaires partagés (validators, throttles, stats, search) |
| `crm`         | Clients, portefeuilles, transferts de portefeuille           |
| `sales`       | Ventes à crédit                                            |
| `receivables` | Dettes, échéances, recouvrements                           |
| `reporting`   | Tableau de bord, aging, évolution                           |

---

## Mise en route (résumé)

```bash
poetry install
cp .env.example .env          # puis renseigner les variables
poetry run python manage.py migrate
poetry run python manage.py createsuperuser
poetry run python manage.py seed_rbac_v2   # rôles & permissions (recommandé)
poetry run python manage.py runserver
```

Tests :

```bash
poetry run pytest
```

---

## Références & documents

- `docs/Fonctionnalité-Control.txt` — spécifications fonctionnelles (assignation /
  transfert de portefeuille).
- `docs/` (racine du dépôt) — cas d'utilisation (`*.xlsx`), diagramme de classes,
  rapport « créance concession auto ».
- `README.md` — démarrage rapide et installation.
- `rbac/fixtures/permissions_config.json` — catalogue des permissions et rôles.
