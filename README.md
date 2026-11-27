# Detecteur et Simulateur d'Interblocages (Theme 6)

**Module :** Advanced Operating Systems (AOS) — 4eme Annee Ingenieur (Securite Informatique)
**Universite :** USTO-MB — Faculte des Mathematiques et de l'Informatique
**Binome :** OUHASSINE Louai & MOUALEK Mehdi Racim

## 1. Presentation

Simulateur concurrent en Python 3.11+ modelisant des processus (threads) et des ressources partagees (mono-instance et multi-instance), construisant dynamiquement un graphe d'attente (Wait-For Graph), detectant les cycles par parcours en profondeur (DFS) et resolvant les interblocages par selection et preemption d'une victime.

Fonctionnalites incluses :
- Extension de prevention par ordre total d'acquisition des ressources (brise l'attente circulaire).
- Equite FIFO sur les files d'attente et gestion des delais maximaux (timeouts).
- Gestion stricte des erreurs (sans `except: pass`) et terminaison propre (`Ctrl+C`).
- Interface graphique Tkinter pour la visualisation en direct.

## 2. Architecture du Projet

    AOSProject/
    |-- src/deadlock_simulator/
    |   |-- domain/           # Processus (etats Linux R, S, D, T, Z, I), ressources, evenements, exceptions
    |   |-- core/             # ResourceManager, Wait-For Graph, detecteur DFS, recuperation, ordre total
    |   |-- concurrency/      # Orchestration des threads, demon detecteur, arret propre (Ctrl+C)
    |   |-- scenarios/        # 5 scenarios : safe, deadlock, philosophers, prevention, errors
    |   |-- cli.py            # Interface ligne de commande avec validation des entrees
    |   |-- gui.py            # Interface graphique Tkinter (demonstration en direct)
    |   `-- logging_config.py # Journalisation formatee (Date, Niveau, PID, Thread, Tache, Code)
    |-- tests/                # Tests unitaires et d'integration (invariants, FIFO, DFS, prevention)
    |-- experiments/          # Scripts de benchmark (N = 2..20) et generation des graphiques
    |-- docs/                 # Rapport LaTeX (docs/report/) et presentation Beamer (docs/presentation/)
    `-- logs/                 # Traces d'execution generees automatiquement (simulation.log)

## 3. Installation

Python 3.11+ requis. Le moteur et la GUI utilisent uniquement la bibliotheque standard Python ; `matplotlib` est requis uniquement pour les graphiques.

    python -m pip install -e .
    python -m pip install -r requirements.txt

## 4. Utilisation

### Ligne de commande (CLI)

    python -m src.deadlock_simulator --scenario safe
    python -m src.deadlock_simulator --scenario deadlock
    python -m src.deadlock_simulator --scenario philosophers
    python -m src.deadlock_simulator --scenario prevention
    python -m src.deadlock_simulator --scenario errors
    python -m src.deadlock_simulator --scenario invalid_name

### Interface Graphique (GUI Tkinter)

    python -m src.deadlock_simulator.gui

## 5. Tests & Experimentations

    python -m unittest tests/test_simulator.py -v
    python -m experiments.run_benchmarks
    python -m experiments.generate_charts

Les parametres (`params.json`), resultats bruts (`experimental_data.csv`) et graphiques (`performance_dfs.png`) sont enregistres dans `experiments/results/`. Les traces sont ecrites dans `logs/simulation.log`.
