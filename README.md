# Détecteur et simulateur d’interblocages

Projet du module **Advanced Operating Systems**. L’application simule les demandes, allocations et libérations de ressources, construit un graphe d’attente, détecte les cycles et applique une politique de récupération.

## Démarrage

Python 3.11 ou plus récent est requis. Aucune dépendance externe n’est nécessaire.

```powershell
python -m src.deadlock_simulator --scenario deadlock
```

Une fois le paquet installé en mode éditable (`python -m pip install -e .`), utiliser `deadlock-sim --scenario safe` ou `deadlock-sim --scenario deadlock`.

## Organisation

- `src/deadlock_simulator/domain/` : processus, ressources et événements.
- `src/deadlock_simulator/core/` : allocations, graphe, détection et récupération.
- `src/deadlock_simulator/concurrency/` : orchestration concurrente et arrêt propre.
- `src/deadlock_simulator/scenarios/` : cas sans interblocage et avec interblocage.
- `tests/` : tests unitaires et d’intégration à compléter.
- `experiments/` : paramètres, résultats bruts, tableaux et graphiques.
- `docs/report/` et `docs/presentation/` : rapport LaTeX et présentation Beamer.

## Architecture concurrente

Le prototype utilise des threads : le simulateur est une application locale légère, et les threads permettent de montrer des opérations concurrentes partageant un gestionnaire de ressources. L’état partagé est encapsulé dans `ResourceManager` et protégé par un verrou. Les activités doivent coopérer avec le mécanisme d’arrêt et respecter un délai maximal. Le choix devra être comparé et justifié dans le rapport final.

## Modèle initial

Chaque ressource représente une seule instance (un seul propriétaire à la fois). Les états des processus reprennent les codes Linux : `R` (en exécution ou prêt), `S` (attente interruptible), `D` (attente noyau non interruptible), `T` (arrêté ou suivi), `Z` (terminé en attente de récupération) et `I` (thread noyau inactif). Dans ce simulateur, une attente de ressource est représentée par `S`, tandis que `D`, `T` et `I` sont disponibles pour des scénarios adaptés. La prise en charge de plusieurs exemplaires d'une même ressource pourra être ajoutée dans une étape ultérieure.

## Progression proposée

1. Compléter les règles de gestion (instances multiples, équité, délais).
2. Ajouter les tests des invariants, cycles et politiques de récupération.
3. Mesurer les temps de détection et de récupération sur des jeux de données reproductibles.
4. Produire le rapport LaTeX, les tableaux/graphes et les diapositives Beamer.

Les journaux sont écrits dans `logs/` au lancement. Les résultats d’expérimentation doivent être conservés dans `experiments/results/` avec leurs paramètres d’entrée.
