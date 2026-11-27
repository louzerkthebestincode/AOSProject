# Expériences reproductibles

Le premier protocole mesure `find_cycles` sur des graphes d'attente en chaîne, avec et sans cycle. La taille, les scénarios et le nombre de répétitions se règlent dans `configurations/detector_benchmark.json`.

Depuis la racine du projet, lancer :

```powershell
.\.venv\Scripts\python.exe experiments\run_detector_benchmark.py
```

Chaque lancement conserve les échantillons individuels en JSON Lines dans `results/raw/`, un résumé CSV dans `results/tables/` et un graphique SVG dans `results/figures/`. Les fichiers enregistrent l'identifiant d'exécution, le scénario, le nombre de nœuds et d'arêtes, le numéro de répétition, la durée mesurée, le nombre de cycles détectés ainsi que la version Python et la plateforme. Les temps dépendent de la machine et de sa charge; comparer des exécutions uniquement dans des conditions similaires.

Pour personnaliser une exécution :

```powershell
.\.venv\Scripts\python.exe experiments\run_detector_benchmark.py --config experiments\configurations\detector_benchmark.json --run-id detector_local_01
```
