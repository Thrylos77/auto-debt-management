# Vague 4 — Lot 6

## Périmètre

Cette première partie de la Vague 4 couvre le Lot 6 : reporting, événements
internes et audit des mutations métier critiques. Le hardening et la suppression
définitive du contrat legacy ont ensuite été réalisés dans la seconde partie de
la Vague 4.

## Changements structurants

- `core` ne possède plus les services de recherche fédérée ni les agrégations métier du dashboard.
- Les services `dashboard_services.py` et `search_services.py` appartiennent désormais à `reporting`.
- Les endpoints V1 `/api/v1/dashboard/summary/` et `/api/v1/search/` restent inchangés pour les clients.
- `core/events.py` est le point de définition des événements internes partagés.
- Les services `users` consomment les événements depuis `core.events`.
- Les événements CRM, Sales et Receivables passent par `core.events` et sont consommables par `audit`.
- Les mutations critiques de portefeuille, de vente et de recouvrement disposent de policies au niveau service.
- Le contrat `/api/core/` avait été conservé pendant la phase de transition ; il est désormais supprimé avec les autres routes legacy.

## URLs Users

Le test de structure Users utilise les résolveurs Django directement. Il ne dépend
pas d'un chemin physique vers `config/v1_urls.py`.
